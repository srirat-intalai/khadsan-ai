# สร้าง User data ของ EC2 (ใช้โดย step3_web_server.py หรือรันเองเพื่อดูสคริปต์ : python3 aws/userdata.py)
# รอ RDS พร้อม แล้วใส่ค่าครบ (endpoint / รหัส DB / bucket / SNS ARN)
# โค้ดเว็บ : EC2 git clone branch aws-workshop ของ repo KhadSan AI
#           (เว็บ + ส่วนต่อ S3 / RDS / SNS + หน้า /history อยู่ใน branch นี้ ส่วน main ของวิชา CS461 ไม่ถูกแตะ)
# เก็บสำเนาไว้ที่ ~/khadsan-userdata.sh (มีรหัส DB ห้ามแชร์)
#
# ตัวเลือก
#   --alert N        คัดออกตั้งแต่ N ลูกในรูปเดียวส่งอีเมลเตือน (ไม่ใส่ = 3)
#   --site URL       ลิงก์เว็บ ใส่ในอีเมลเตือน (ไม่ใส่ก็ได้)
#   --branch NAME    branch ของ GitHub (ไม่ใส่ = aws-workshop)
#   --zip            ไม่ใช้ GitHub : ส่งโฟลเดอร์ web/ ใน CloudShell (รวมโมเดล) ผ่าน S3 ลิงก์ชั่วคราว 6 ชม. แทน

import argparse
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *   # noqa: F401,F403

REPO = "https://github.com/srirat-intalai/khadsan-ai.git"
BRANCH = "aws-workshop"            # main = งานวิชา CS461 ห้ามแตะ
RDS_CA = "https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem"

TEMPLATE = r"""#!/bin/bash
# KhadSan AI : ติดตั้งเว็บบน Ubuntu 24.04 (สร้างโดย aws/userdata.py) ดู log ที่ /var/log/khadsan-setup.log
set -euxo pipefail
exec > >(tee -a /var/log/khadsan-setup.log) 2>&1
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
# libgl1 : OpenCV (ที่ ultralytics ลงมา) ต้องใช้ libGL.so.1 ไม่มีแล้ว import โมเดลไม่ได้ เว็บจะขึ้น "AI ตรวจไม่ได้"
apt-get install -y python3 python3-venv python3-pip curl git libgl1

# swap 4 GB : t3.small มีแรม 2 GB ตอนลง/โหลด PyTorch ไม่พอ
if ! swapon --show=NAME --noheadings | grep -q /swapfile; then
    if [ ! -f /swapfile ]; then
        fallocate -l 4G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
    fi
    swapon /swapfile
fi
grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab

__GET_CODE__
cd /opt/khadsan-ai/web
python3 -m venv /opt/khadsan-venv
/opt/khadsan-venv/bin/python -m pip install --upgrade pip
/opt/khadsan-venv/bin/pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
/opt/khadsan-venv/bin/pip install --no-cache-dir -r requirements.txt

# ใบรับรองของ RDS : เว็บต่อ MySQL แบบเข้ารหัสและตรวจใบรับรอง
curl -fsSL -o /opt/khadsan-rds-ca.pem __RDS_CA__

# ค่าลับ อ่านได้แค่ root (systemd ส่งให้เว็บเป็น environment variable)
cat > /etc/khadsan.env <<'EOF'
__ENV__
EOF
chmod 600 /etc/khadsan.env

cat > /etc/systemd/system/khadsan.service <<'EOF'
[Unit]
Description=KhadSan AI Flask Web
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/khadsan-ai/web
EnvironmentFile=/etc/khadsan.env
Environment=OMP_NUM_THREADS=1
Environment=MALLOC_ARENA_MAX=2
Environment=WARMUP=1
# worker เดียว (โมเดลกินแรม) หลาย thread (โมเดลตรวจทีละงานด้วย model_lock ใน app.py)
ExecStart=/opt/khadsan-venv/bin/gunicorn --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:__PORT__ app:app
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

chown -R ubuntu:ubuntu /opt/khadsan-ai
systemctl daemon-reload
systemctl enable khadsan
systemctl restart khadsan
echo "KHADSAN SETUP COMPLETE"
"""


LINK_HOURS = 6
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


# zip โฟลเดอร์ web/ (โค้ด + โมเดล) ขึ้น S3 แล้วคืนลิงก์ชั่วคราวให้ EC2 ดาวน์โหลด
def upload_web(s3, bucket):
    if not os.path.exists(os.path.join(WEB_DIR, "app.py")) or not os.path.exists(os.path.join(WEB_DIR, "models", "best_detect.pt")):
        sys.exit("ไม่พบ web/app.py หรือ web/models/best_detect.pt ข้างๆ โฟลเดอร์ aws/ (อัปโหลด khadsan-aws.zip ให้ครบก่อน)")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(WEB_DIR):
            dirs[:] = [d for d in dirs if d not in ("venv", "__pycache__", ".git")]
            for f in files:
                if f.endswith(".pyc") or f == ".DS_Store":
                    continue
                full = os.path.join(root, f)
                z.write(full, os.path.join("web", os.path.relpath(full, WEB_DIR)))
    data = buf.getvalue()
    s3.put_object(Bucket=bucket, Key="deploy/web.zip", Body=data, ContentType="application/zip")
    print("อัปโค้ดเว็บขึ้น s3://" + bucket + "/deploy/web.zip แล้ว (%.1f MB)" % (len(data) / 1e6))
    return s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": "deploy/web.zip"},
                                     ExpiresIn=LINK_HOURS * 3600)


def env_line(key, value):
    # รูปแบบ EnvironmentFile ของ systemd : ใส่ " ครอบ และ escape \ กับ "
    return key + '="' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def build(s, alert=3, site="", use_zip=False, branch=BRANCH):
    """คืน (สคริปต์ User data, RDS endpoint, bucket) และเขียนสำเนาไว้ที่ ~/khadsan-userdata.sh"""
    env = load_env()
    if "DB_PASSWORD" not in env:
        sys.exit("ไม่พบรหัส DB ใน " + ENV_FILE + " ให้รัน python3 aws/step1_network_db.py ก่อน")
    s3 = s.client("s3")
    bucket = pick_bucket(s3, env)
    if not bucket:
        sys.exit("ไม่พบ S3 bucket ให้รัน python3 aws/step2_storage_alerts.py ก่อน")
    topic = env.get("SNS_TOPIC_ARN") or find_topic_arn(s.client("sns"))
    if not topic or not topic.startswith("arn:aws:sns:"):
        sys.exit("ไม่พบ SNS topic " + TOPIC + " ให้รัน python3 aws/step2_storage_alerts.py ก่อน")

    rds = s.client("rds")
    db = rds.describe_db_instances(DBInstanceIdentifier=DB_ID)["DBInstances"][0]
    if db["DBInstanceStatus"] != "available":
        print("  รอ RDS " + DB_ID + " พร้อม (ตอนนี้ " + db["DBInstanceStatus"] + ") เช็กทุก 30 วินาที ...")
        rds.get_waiter("db_instance_available").wait(DBInstanceIdentifier=DB_ID,
                                                     WaiterConfig={"Delay": 30, "MaxAttempts": 60})
        db = rds.describe_db_instances(DBInstanceIdentifier=DB_ID)["DBInstances"][0]
    endpoint = db["Endpoint"]["Address"]
    print("  RDS พร้อม : " + endpoint)

    values = [
        ("PORT", PORT), ("AWS_REGION", REGION),
        ("S3_BUCKET", bucket), ("SNS_TOPIC_ARN", topic), ("ALERT_ROTTEN", max(1, int(alert))),
        ("DB_HOST", endpoint), ("DB_USER", env.get("DB_USER", DB_USER)),
        ("DB_PASSWORD", env["DB_PASSWORD"]), ("DB_NAME", env.get("DB_NAME", DB_NAME)),
        ("DB_SSL_CA", "/opt/khadsan-rds-ca.pem"),
    ]
    if site:
        values.append(("SITE_URL", site.rstrip("/")))
    if use_zip:
        url = upload_web(s3, bucket)
        get_code = ("# โค้ดเว็บจาก S3 (deploy/web.zip) ลิงก์ชั่วคราว ใช้ได้ " + str(LINK_HOURS) + " ชั่วโมง\n"
                    "if [ ! -f /opt/khadsan-ai/web/app.py ]; then\n"
                    "    mkdir -p /opt/khadsan-ai\n"
                    "    curl -fsSL -o /tmp/khadsan-web.zip '" + url + "'\n"
                    "    python3 -m zipfile -e /tmp/khadsan-web.zip /opt/khadsan-ai/\n"
                    "fi")
    else:
        get_code = ("# เว็บ KhadSan AI + ส่วนต่อ AWS จาก GitHub branch " + branch + " (เอาแค่เวอร์ชันล่าสุด)\n"
                    "if [ ! -d /opt/khadsan-ai/.git ]; then\n"
                    "    git clone --depth 1 --branch " + branch + " " + REPO + " /opt/khadsan-ai\n"
                    "fi\n"
                    "test -f /opt/khadsan-ai/web/cloud.py\n"
                    "test -f /opt/khadsan-ai/web/models/best_detect.pt")
    script = (TEMPLATE.replace("__ENV__", "\n".join(env_line(k, v) for k, v in values))
              .replace("__GET_CODE__", get_code)
              .replace("__RDS_CA__", RDS_CA).replace("__PORT__", str(PORT)))

    out = os.path.expanduser("~/khadsan-userdata.sh")
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(script)
    save_env({"S3_BUCKET": bucket, "SNS_TOPIC_ARN": topic, "DB_HOST": endpoint})
    return script, endpoint, bucket


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alert", type=int, default=3)
    ap.add_argument("--site", default="")
    ap.add_argument("--branch", default=BRANCH)
    ap.add_argument("--zip", action="store_true")
    args = ap.parse_args()
    script, endpoint, bucket = build(session(), args.alert, args.site, args.zip, args.branch)
    print("=" * 20 + " User data (สำเนาที่ ~/khadsan-userdata.sh มีรหัส DB ห้ามแชร์) " + "=" * 20)
    print(script, end="")
    print("=" * 20 + " จบ User data " + "=" * 20)
    print("ปกติไม่ต้องคัดลอกเอง : python3 aws/step3_web_server.py จะ Launch EC2 ให้")


if __name__ == "__main__":
    main()
