# ต่อ AWS : เก็บรูปตีกรอบ + log (JSON) ใน S3 / ประวัติใน RDS (MySQL) / อีเมลเตือนผ่าน SNS
# เปิดเองเมื่อตั้ง environment variable ไว้ ไม่ตั้ง = เว็บทำงานเหมือนเดิม (รันบนโน้ตบุ๊กได้ ไม่ต้องมี AWS)
#
#   S3_BUCKET       ชื่อ bucket เก็บรูปและ log            เช่น khadsan-images-1660705185
#   DB_HOST         endpoint ของ RDS                       เช่น khadsan-db.xxxx.us-east-1.rds.amazonaws.com
#   DB_USER         ผู้ใช้ฐานข้อมูล (ไม่ตั้ง = admin)
#   DB_PASSWORD     รหัสฐานข้อมูล
#   DB_NAME         ชื่อฐานข้อมูล (ไม่ตั้ง = khadsan)
#   DB_SSL_CA       ไฟล์ใบรับรองของ RDS (ไม่มี = ยังเข้ารหัส แต่ไม่ตรวจใบรับรอง)
#   SNS_TOPIC_ARN   ARN ของ topic khadsan-alerts
#   ALERT_ROTTEN    เจอลูกคัดออกตั้งแต่กี่ลูกในรูปเดียวถึงส่งอีเมลเตือน (ไม่ตั้ง = 3)
#   SITE_URL        ลิงก์ https ของเว็บ (CloudFront) ใส่ในอีเมลเตือน ไม่บังคับ
#   AWS_REGION      ไม่ตั้ง = us-east-1
#
# สิทธิ์ AWS มาจาก IAM role ของ EC2 (Learner Lab = LabInstanceProfile → LabRole) ไม่ใส่ Access Key ในโค้ด

import io
import os
import json
import uuid
import logging
import threading
from datetime import datetime, timezone, timedelta

log = logging.getLogger("khadsan.cloud")

THAI_TZ = timezone(timedelta(hours=7))   # เวลาไทย ให้ตรงกับ Lambda สรุปรายวัน

REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET = os.environ.get("S3_BUCKET", "").strip()
DB_HOST = os.environ.get("DB_HOST", "").strip()
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "khadsan")
DB_SSL_CA = os.environ.get("DB_SSL_CA", "")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "").strip()
SITE_URL = os.environ.get("SITE_URL", "").strip().rstrip("/")
try:
    ALERT_ROTTEN = max(1, int(os.environ.get("ALERT_ROTTEN", "3")))
except ValueError:
    ALERT_ROTTEN = 3

STORAGE_ON = bool(S3_BUCKET)
DB_ON = bool(DB_HOST and DB_PASSWORD)
ALERT_ON = bool(SNS_TOPIC_ARN)
ENABLED = STORAGE_ON or DB_ON or ALERT_ON

HISTORY_LIMIT = 20          # หน้า /history โชว์กี่ครั้งล่าสุด
LINK_SECONDS = 3600         # ลิงก์รูปจาก S3 (presigned URL) ใช้ได้กี่วินาที
SAVE_MAX_SIDE = 1600        # ย่อรูปก่อนเก็บ ประหยัดที่ S3

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS scans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    total INT,
    fresh INT,
    rotten INT,
    recheck INT,
    image_key VARCHAR(255),
    INDEX (created_at)
)
"""

_clients = {}
_clients_lock = threading.Lock()
_table_ready = False


# สร้าง client ของ boto3 ครั้งแรกที่ใช้ (import ตอนใช้ เว็บที่ไม่ได้ต่อ AWS ไม่ต้องลง boto3)
def _client(name):
    with _clients_lock:
        if name not in _clients:
            import boto3
            from botocore.config import Config
            config = Config(region_name=REGION, retries={"max_attempts": 3}, connect_timeout=5, read_timeout=10)
            _clients[name] = boto3.client(name, config=config)
        return _clients[name]


# ต่อ RDS ใหม่ทุกครั้ง (คนใช้น้อย ไม่ต้องทำ pool) และเข้ารหัสการเชื่อมต่อเสมอ
def _db():
    global _table_ready
    import pymysql
    if DB_SSL_CA and os.path.exists(DB_SSL_CA):
        ssl = {"ca": DB_SSL_CA}
    else:
        ssl = {"fake_flag_to_enable_tls": True}   # วิธีของ PyMySQL : เปิด TLS โดยไม่ตรวจใบรับรอง
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME,
                           ssl=ssl, connect_timeout=5, read_timeout=10, write_timeout=10,
                           charset="utf8mb4", autocommit=True,
                           cursorclass=pymysql.cursors.DictCursor)
    if not _table_ready:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE)   # สร้างตารางเองถ้ายังไม่มี
        _table_ready = True
    return conn


def _jpeg(img):
    temp = img.copy()
    temp.thumbnail((SAVE_MAX_SIDE, SAVE_MAX_SIDE))
    buf = io.BytesIO()
    temp.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


# ===== หลังตรวจรูปเสร็จ =====
# boxed_img = รูปที่ตีกรอบแล้ว / summary = ผลจาก count_states() ใน app.py
# พังตรงไหนก็ไม่ทำให้หน้าผลตรวจพัง แค่บอกว่าบันทึกไม่สำเร็จ
def save_scan(boxed_img, summary):
    result = {"enabled": ENABLED, "saved_s3": False, "saved_db": False, "alerted": False, "error": False}
    if not ENABLED:
        return result

    now = datetime.now(THAI_TZ)
    day = now.date().isoformat()
    scan_id = now.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    image_key = "images/" + day + "/" + scan_id + ".jpg"
    record = {
        "id": scan_id,
        "created_at": now.isoformat(timespec="seconds"),   # Lambda ดู 10 ตัวแรก (วันที่ตามเวลาไทย)
        "total": summary["total"],
        "fresh": summary["good"],
        "rotten": summary["bad"],
        "recheck": summary["check"],
        "rotten_percent": summary["bad_percent"],
        "kinds": dict(summary["kinds"]),
        "image_key": image_key if STORAGE_ON else None,
    }

    # 1) S3 : รูปตีกรอบ + log JSON (Lambda อ่าน log ไปสรุปตอน 18:00)
    if STORAGE_ON:
        try:
            s3 = _client("s3")
            s3.put_object(Bucket=S3_BUCKET, Key=image_key, Body=_jpeg(boxed_img), ContentType="image/jpeg")
            s3.put_object(Bucket=S3_BUCKET, Key="logs/" + day + "/" + scan_id + ".json",
                          Body=json.dumps(record, ensure_ascii=False).encode("utf-8"),
                          ContentType="application/json")
            result["saved_s3"] = True
        except Exception:
            log.exception("save to S3 failed")
            result["error"] = True

    # 2) RDS : 1 แถวต่อการตรวจ 1 ครั้ง ให้หน้า /history (เวลาเป็นเวลาไทย)
    if DB_ON:
        try:
            conn = _db()
            try:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO scans (created_at, total, fresh, rotten, recheck, image_key) "
                                "VALUES (%s, %s, %s, %s, %s, %s)",
                                (now.strftime("%Y-%m-%d %H:%M:%S"), record["total"], record["fresh"],
                                 record["rotten"], record["recheck"], record["image_key"]))
            finally:
                conn.close()
            result["saved_db"] = True
        except Exception:
            log.exception("save to RDS failed")
            result["error"] = True

    # 3) SNS : ลูกคัดออกถึงเกณฑ์ ส่งอีเมลเตือนทันที
    if ALERT_ON and summary["bad"] >= ALERT_ROTTEN:
        try:
            lines = [
                "KhadSan AI พบลูกที่ต้องคัดออก " + str(summary["bad"]) + " ลูก จาก " + str(summary["total"]) + " ลูก ("
                + str(summary["bad_percent"]) + "%)",
                "",
                "เวลา: " + now.strftime("%Y-%m-%d %H:%M:%S") + " (เวลาไทย)",
                "สด: " + str(summary["good"]) + " / ให้ตรวจซ้ำ: " + str(summary["check"]) + " / คัดออก: " + str(summary["bad"]),
                "ชนิด: " + ", ".join(k + " " + str(n) for k, n in summary["kinds"]),
                "ลูกเลขที่ต้องคัดออก: " + ", ".join(summary["bad_nums"]),
            ]
            if STORAGE_ON:
                lines.append("รูปใน S3: s3://" + S3_BUCKET + "/" + image_key)
            if SITE_URL:
                lines.append("ดูประวัติ: " + SITE_URL + "/history")
            lines += ["", "เกณฑ์เตือน: คัดออกตั้งแต่ " + str(ALERT_ROTTEN) + " ลูกในรูปเดียว"]
            # Subject ใช้ภาษาอังกฤษ (บางโปรแกรมอีเมลแสดงหัวเรื่องภาษาไทยเพี้ยน)
            _client("sns").publish(TopicArn=SNS_TOPIC_ARN,
                                   Subject="KhadSan AI Alert - " + str(summary["bad"]) + " rotten fruits found",
                                   Message="\n".join(lines))
            result["alerted"] = True
        except Exception:
            log.exception("SNS publish failed")
            result["error"] = True

    return result


# ===== หน้า /history =====
# 20 ครั้งล่าสุด + ยอดรวมของวันนี้ รูปเปิดผ่าน presigned URL (bucket เป็นส่วนตัว)
def history():
    data = {"enabled": DB_ON, "error": False, "scans": [], "today": None, "alert_rotten": ALERT_ROTTEN}
    if not DB_ON:
        return data
    try:
        conn = _db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, created_at, total, fresh, rotten, recheck, image_key "
                            "FROM scans ORDER BY id DESC LIMIT %s", (HISTORY_LIMIT,))
                scans = cur.fetchall()
                today = datetime.now(THAI_TZ).strftime("%Y-%m-%d")
                cur.execute("SELECT COUNT(*) AS scans, COALESCE(SUM(total), 0) AS total, "
                            "COALESCE(SUM(fresh), 0) AS fresh, COALESCE(SUM(rotten), 0) AS rotten, "
                            "COALESCE(SUM(recheck), 0) AS recheck FROM scans "
                            "WHERE created_at >= %s AND created_at < %s + INTERVAL 1 DAY", (today, today))
                data["today"] = cur.fetchone()
                data["today"]["date"] = today
        finally:
            conn.close()
    except Exception:
        log.exception("read history from RDS failed")
        data["error"] = True
        return data

    for row in scans:
        row["percent"] = round(row["rotten"] * 100 / row["total"]) if row["total"] else 0
        row["time"] = row["created_at"].strftime("%Y-%m-%d %H:%M") if row["created_at"] else ""
        row["image_url"] = None
        if STORAGE_ON and row["image_key"]:
            try:
                row["image_url"] = _client("s3").generate_presigned_url(
                    "get_object", Params={"Bucket": S3_BUCKET, "Key": row["image_key"]}, ExpiresIn=LINK_SECONDS)
            except Exception:
                log.exception("presign failed")
        data["scans"].append(row)
    return data
