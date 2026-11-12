# Workshop : KhadSan AI บน AWS (Learner Lab)

ถ่ายรูปผลไม้ → AI (YOLOv8n) ตีกรอบบอกทุกลูกว่าสดหรือเน่า → เก็บรูปและประวัติไว้ดูย้อนหลัง → เจอลูกเน่าเยอะส่งอีเมลเตือนทันที → ทุกวัน 18:00 ส่งอีเมลสรุปของวัน

ทำตามแบบ Lab 12 (Cloud Automation) : แต่ละขั้นรัน **สคริปต์คำสั่งเดียว** ใน CloudShell แล้วไป **ดูผลใน Console** ว่าบริการถูกสร้างจริง จบด้วยเว็บที่ใช้งานได้ + สคริปต์ตรวจ ✅ + สคริปต์ลบ

โค้ดทั้งหมดอยู่ใน branch **`aws-workshop`** ของ repo KhadSan AI (branch `main` เป็นงานวิชา CS461)

**บริการที่นับในเกณฑ์ (8 ตัว)** : EC2, EBS, S3, RDS, CloudFront, SNS, Lambda, EventBridge

**บริการพื้นฐานที่ทุกระบบต้องมี (สีม่วงในโจทย์ ไม่นับในเกณฑ์ 4 บริการ แต่ต้องมี)**

| บริการ | ในระบบนี้ |
|---|---|
| IAM | LabRole ให้ EC2 เขียน S3 / ส่ง SNS และให้ Lambda อ่าน S3 โดยไม่มี Access Key ในโค้ด + สิทธิ์ให้ EventBridge เรียก Lambda |
| VPC | EC2 และ RDS อยู่ใน default VPC, Security Group `khadsan-web-sg` (7860) และ `khadsan-db-sg` (3306 เฉพาะจากเว็บ) |
| CLI | คำสั่ง `aws ...` และสคริปต์ทุกขั้นที่รันใน CloudShell |
| CloudWatch | log ของ Lambda (`/aws/lambda/KhadsanDailySummary`) ดูตอนทดสอบ/error, กราฟ CPU ของ EC2 / RDS |
| Cost & Usage Report | ดูค่าใช้จ่าย : `check.py` ลองอ่าน Cost Explorer ถ้า Learner Lab ไม่ให้อ่าน ดู Used $ / Budget ที่หน้า Lab |

## Architecture

```
ผู้ใช้ (มือถือ / คอม)
   │ https
   ▼
CloudFront ──http:7860──▶ EC2 (Flask + YOLOv8n, ดิสก์ EBS)
                              ├──▶ S3   รูปตีกรอบ images/ + log logs/*.json
                              ├──▶ RDS  MySQL ตาราง scans (หน้า /history)
                              └──▶ SNS  อีเมลเตือนทันทีเมื่อคัดออก ≥ 3 ลูก
EventBridge (ทุกวัน 18:00) ──▶ Lambda ──อ่าน log วันนี้จาก S3──▶ SNS อีเมลสรุป
```

## เส้นชัย (ต้องเห็นครบทุกข้อ)

| # | ต้องเห็น | พิสูจน์บริการ |
|---|---|---|
| 1 | เปิด `https://xxxx.cloudfront.net` แล้วถ่าย/อัปรูปผลไม้ ได้ผลตีกรอบ | CloudFront, EC2, EBS |
| 2 | ใต้ผลขึ้น "บันทึกผลนี้แล้ว" และ `aws s3 ls` เห็นรูป | S3 |
| 3 | หน้า **ประวัติการตรวจ** (/history) มีรายการที่เพิ่งสแกน | RDS |
| 4 | รูปที่มีลูกเน่า ≥ 3 ลูก → ได้อีเมลเตือน | SNS |
| 5 | Lambda ทดสอบแล้วได้อีเมลสรุป (ตัวเลขตรงกับที่สแกน) และ rule 18:00 Enabled | Lambda, EventBridge, SNS |
| 6 | `python3 aws/check.py` ขึ้น ✅ | ทั้งหมด |

## ลำดับและเวลา (ค่าประมาณ ต้องจับเวลาตอนซ้อมแล้วแก้)

| ขั้น | สคริปต์ | สร้าง | รอ |
|---|---|---|---|
| 0 | `git clone` | – | – |
| 1 | `step1_network_db.py` | Security Group 2 ตัว + **RDS** | RDS ราว 10 นาที (ทำขั้นต่อไปได้เลย) |
| 2 | `step2_storage_alerts.py` | **S3** + **SNS** | กด Confirm ในอีเมล |
| 3 | `step3_web_server.py` | **EC2** + **EBS** | รอ RDS พร้อมก่อน แล้วเครื่องติดตั้งเว็บเองราว 10-15 นาที |
| 4 | `step4_automation.py` | **Lambda** + **EventBridge** | ทำระหว่างรอ EC2 |
| 5 | `step5_cloudfront.py` | **CloudFront** | Deploy ราว 5-10 นาที |
| 6 | ทดสอบเว็บ | – | – |
| 7 | `check.py` | – | – |
| 8 | `cleanup.py` | ลบทุกอย่าง | CloudFront ลบได้หลัง Disable ราว 5-15 นาที |

> **ระบบเดโมของทีม** : ทำขั้น 0-7 แล้ว **ไม่ต้องทำขั้น 8** เก็บไว้ใช้วันเดโม (ดูหัวข้อ "เปิด Lab ใหม่")
> **กลุ่มที่ทำ workshop** : ทำขั้น 0-8 ครบ **ห้ามข้ามขั้น 8** End Lab แค่หยุดเครื่อง ไม่ได้ลบ RDS / CloudFront / EBS ที่ค้างยังกินเครดิต Lab

---

## ขั้น 0 : เตรียม CloudShell

1. Learner Lab → **Start Lab** รอไฟเขียว → กด **AWS** เปิด Console ดูว่า region เป็น **N. Virginia (us-east-1)**
2. ดูเครดิตที่เหลือในหน้า Lab (Used $ / Budget)
3. กดไอคอน **CloudShell** (ข้างช่อง Search) แล้วรัน
   ```bash
   cd ~ && git clone -b aws-workshop --depth 1 https://github.com/srirat-intalai/khadsan-ai.git
   cd ~/khadsan-ai && ls aws/
   aws sts get-caller-identity
   echo $AWS_REGION
   ```

**ต้องเห็น** : `step1_network_db.py` ... `step5_cloudfront.py`, `check.py`, `cleanup.py`, Arn มี `assumed-role/voclabs` และ `us-east-1`
**ถ้า error** `No space left on device` : พื้นที่ CloudShell (1 GB) เต็ม → `du -sh ~/* ~/.[!.]* 2>/dev/null | sort -h | tail` ดูว่าอะไรกิน แล้วลบของที่ไม่ใช้ (เช่น clone เก่า `rm -rf ~/khadsan-ai`) หรือ Actions → Delete (ล้าง CloudShell ทั้งหมด)
**ถ้า error** `destination path 'khadsan-ai' already exists` : มี clone เก่า → `rm -rf ~/khadsan-ai` แล้ว clone ใหม่

> ใส่ `-b aws-workshop` ทุกครั้ง (ไม่ใส่จะได้ branch main ซึ่งไม่มีโฟลเดอร์ aws/) และ `--depth 1` เอาแค่เวอร์ชันล่าสุด ไม่ให้พื้นที่เต็ม
> ทุกคำสั่งต่อจากนี้รันใน `~/khadsan-ai` ถ้าเปิด CloudShell ใหม่ ให้ `cd ~/khadsan-ai` ก่อน
> **คัดลอกคำสั่งจากไฟล์นี้ ไม่ใช่จากสไลด์ PDF** (คัดลอกจาก PDF บรรทัดจะถูกตัด/ย่อหน้าหาย)

## ขั้น 1 : Security Group + RDS

```bash
python3 aws/step1_network_db.py
```
ตั้งรหัสผ่านฐานข้อมูล 8-41 ตัว ห้ามมี `/ @ " '` และช่องว่าง (พิมพ์แล้วไม่ขึ้นบนจอ) สคริปต์จดไว้ใน `~/khadsan.env` (ห้ามแชร์)

สร้าง : `khadsan-web-sg` (เปิด 7860), `khadsan-db-sg` (MySQL 3306 เฉพาะจาก web-sg), RDS MySQL 8.4 `khadsan-db` (db.t4g.micro, ไม่เปิดสาธารณะ, เข้ารหัส)

**ต้องเห็น** : `พบแล้ว role LabRole`, security group 2 ตัว, `สั่งสร้างแล้ว (ราว 10 นาที)`
**ดูใน Console** : RDS → Databases → `khadsan-db` สถานะ Creating / EC2 → Security Groups
**ไม่ต้องรอ RDS** ไปขั้น 2 ได้เลย

## ขั้น 2 : S3 + SNS

```bash
python3 aws/step2_storage_alerts.py --email อีเมลของคุณ
```
สร้าง : bucket ส่วนตัว `khadsan-images-<เลขบัญชี>` (ปิด public ทั้ง 4 ข้อ) และ SNS topic `khadsan-alerts` + สมัครอีเมล ไม่ต้องสร้างโฟลเดอร์ images/ logs/ เอง

**ต้องทำ** : เปิดอีเมล *AWS Notification - Subscription Confirmation* → กด **Confirm subscription** (ดูใน Junk ด้วย)
**ดูใน Console** : S3 → Buckets / SNS → Topics → `khadsan-alerts` → Subscriptions = **Confirmed**

## ขั้น 3 : EC2 + EBS (เว็บ)

```bash
python3 aws/step3_web_server.py
```
สคริปต์จะ
1. รอ RDS เป็น available (ถ้ายังไม่เสร็จจะเช็กทุก 30 วินาที)
2. สร้าง User data ที่ใส่ค่าครบ (endpoint, รหัส DB, bucket, SNS ARN) **ไม่ต้องคัดลอกไปวางเอง**
3. Launch EC2 `t3.small` Ubuntu 24.04, ดิสก์ **EBS gp3 30 GiB**, IAM profile **LabInstanceProfile**, `khadsan-web-sg`, key `vockey`

EC2 ติดตั้งเว็บเอง : `git clone -b aws-workshop` (เว็บ + ส่วนต่อ S3 / RDS / SNS / หน้า /history) → ลง PyTorch → รันด้วย gunicorn พอร์ต 7860

**ต้องเห็น** : `สร้างแล้ว khadsan-web-...` และคำสั่ง `curl` สำหรับเช็ก
**ดูใน Console** : EC2 → Instances → Running / แท็บ Storage เห็น EBS 30 GiB
**ระหว่างรอติดตั้ง 10-15 นาที ทำขั้น 4 ได้เลย** แล้วค่อยเช็กด้วยคำสั่ง curl ที่สคริปต์พิมพ์ให้ (ได้ `200` = เสร็จ)

มี EC2 เก่าอยู่แล้วและอยากสร้างใหม่แทน : `python3 aws/step3_web_server.py --replace` (สร้างตัวใหม่แล้ว Terminate ตัวเก่า)

## ขั้น 4 : Lambda + EventBridge

```bash
python3 aws/step4_automation.py
```
สร้าง : Lambda `KhadsanDailySummary` (Python 3.12, role LabRole, ตั้ง `S3_BUCKET` / `SNS_TOPIC_ARN` ให้เอง) และ rule `khadsan-daily-1800` = `cron(0 11 * * ? *)` (11:00 UTC = 18:00 เวลาไทย) แล้วเรียก Lambda ทดสอบ 1 ครั้ง

**ต้องเห็น** : `statusCode 200` และได้อีเมล **KhadSan AI Daily Summary - วันนี้** (ยังไม่สแกน ตัวเลข 0 ได้)
**ดูใน Console** : Lambda → `KhadsanDailySummary` → Triggers = EventBridge / EventBridge → Rules → `khadsan-daily-1800` Enabled
**ดู log (CloudWatch)** : CloudWatch → Log groups → `/aws/lambda/KhadsanDailySummary` → stream ล่าสุด ต้องเห็น `START`, `END`, `REPORT ... Duration` (ถ้า Lambda error ข้อความ error จะอยู่ตรงนี้)

> ไม่ต้องสร้าง IAM role ใหม่ (Learner Lab สร้างไม่ได้ จะเจอ `iam:CreateRole` not authorized) สคริปต์ให้สิทธิ์ EventBridge เรียก Lambda ที่ตัว Lambda แทน

## ขั้น 5 : CloudFront (https)

รอให้ curl ในขั้น 3 ได้ `200` ก่อน แล้ว
```bash
python3 aws/step5_cloudfront.py
```
สร้าง distribution ชี้ EC2 พอร์ต 7860 (HTTP only), Redirect HTTP → HTTPS, รับ POST, CachingDisabled, Description `khadsan-ai`

ทำไมต้องมี : เบราว์เซอร์เปิดกล้องได้เฉพาะหน้าเว็บ https และ `*.cloudfront.net` มีใบรับรองให้ ไม่ต้องซื้อโดเมน ยังช่วยกรณี Wi-Fi บล็อกพอร์ต 7860 ด้วย (ผู้ใช้เข้าทาง 443)

**ต้องเห็น** : `ลิงก์เว็บ : https://xxxx.cloudfront.net`
**ดูใน Console** : CloudFront → Distributions → สถานะ Deploying → **Deployed** (ราว 5-10 นาที)
ถ้าสคริปต์บอกว่าสร้างไม่ได้ (สิทธิ์ Lab) มันจะพิมพ์ค่าที่ต้องกรอกใน Console ให้ทำตามนั้น

## ขั้น 6 : ทดสอบ

1. เปิดลิงก์ CloudFront **บนมือถือ** → เปิดกล้อง → ถ่ายผลไม้ → ตรวจ
   **ต้องเห็น** : ผลตีกรอบ และ "บันทึกผลนี้แล้ว" (ถ้ามีลูกเน่า ≥ 3 → "ส่งอีเมลเตือนแล้ว" + ได้อีเมล)
2. กด **ประวัติการตรวจ** → เห็นรายการที่เพิ่งสแกน พร้อมรูป (ข้อมูลจาก RDS)
3. ใน CloudShell
   ```bash
   aws s3 ls s3://$(grep ^S3_BUCKET ~/khadsan.env | cut -d= -f2)/ --recursive | tail -4
   aws lambda invoke --function-name KhadsanDailySummary --cli-binary-format raw-in-base64-out --payload '{}' /tmp/out.json && cat /tmp/out.json; echo
   ```
   **ต้องเห็น** : ไฟล์ `images/<วันนี้>/...jpg` กับ `logs/<วันนี้>/...json` และ `scans` ไม่เป็น 0

## ขั้น 7 : ตรวจงาน

```bash
python3 aws/check.py
```
**ต้องเห็น** : ✅ ทุกบรรทัด (❌ จะบอกว่าต้องแก้อะไร) รวมถึงหมวดบริการพื้นฐาน (CloudWatch มี log ของ Lambda) และบรรทัด ℹ️ ค่าใช้จ่าย

**ดูค่าใช้จ่าย** : หน้า Learner Lab → Used $ / Budget (หรือ Billing and Cost Management → Cost Explorer ถ้าบัญชีเปิดให้)

## ขั้น 8 : Clean up (กลุ่มที่ทำ workshop เท่านั้น)

```bash
python3 aws/cleanup.py
```
พิมพ์ `DELETE` ยืนยัน → ลบ EventBridge, Lambda, CloudFront, EC2 (+EBS), RDS, S3 (+รูปทั้งหมด), SNS, Security group และ `~/khadsan.env` (LabRole ไม่ลบ)
CloudFront ต้อง Disable แล้วรอราว 5-15 นาทีถึงลบได้ สคริปต์รอให้ ถ้า CloudShell หลุด ให้รันซ้ำ
แล้ว **End Lab**

---

## เปิด Lab ใหม่ (เช่น วันเดโม)

Learner Lab หยุด EC2 / RDS ตอนจบ session พอ Start Lab ใหม่ EC2 ได้ Public DNS ใหม่ → CloudFront ขึ้น 502/504
```bash
cd ~/khadsan-ai && python3 aws/fix_origin.py
python3 aws/check.py
```
เปิด EC2 / RDS ที่หยุดอยู่ และแก้ origin ของ CloudFront ให้ชี้ที่ใหม่ รอ Deployed ราว 5 นาที (RDS เปิดใหม่ราว 5 นาที)

## แก้ปัญหา (เจอจริงตอนซ้อม)

| อาการ | สาเหตุ / วิธีแก้ |
|---|---|
| `No space left on device` ตอน clone | CloudShell 1 GB เต็ม (clone ทั้งประวัติราว 110 MB) ใช้ `--depth 1` และลบ clone เก่า ดูขั้น 0 |
| `ls aws/` ไม่เจอโฟลเดอร์ | clone ไม่ได้ใส่ `-b aws-workshop` → `rm -rf ~/khadsan-ai` แล้ว clone ใหม่ |
| `iam:CreateRole` not authorized | กดสร้าง EventBridge ในหน้าเว็บแล้วติ๊ก *Use execution role → Create default role* ไว้ Learner Lab สร้าง role ไม่ได้ ใช้ `step4_automation.py` แทน หรือเอาติ๊กออก |
| Lambda `expected an indented block` | คัดลอกโค้ดจาก PDF แล้วย่อหน้าหาย ใช้ `step4_automation.py` (อัปโค้ดจากไฟล์) |
| Lambda `An ARN must have at least 6 elements` | พิมพ์ SNS ARN เองแล้วขาด `arn:` ข้างหน้า สคริปต์ใส่ให้เอง รัน `step4_automation.py` ซ้ำได้ |
| User data ติดตั้งไม่จบ / `--index-url` error | คัดลอก User data จากสไลด์แล้วบรรทัดถูกตัด ใช้ `step3_web_server.py` |
| `systemctl status khadsan` → could not be found | ยังติดตั้งไม่เสร็จ รอแล้วดู `sudo tail -n 20 /var/log/khadsan-setup.log` บน EC2 ต้องจบด้วย `KHADSAN SETUP COMPLETE` |
| `http://IP:7860` หมุนค้าง แต่ curl บน EC2 ได้ 200 | เครือข่าย (เช่น Wi-Fi มหาวิทยาลัย) บล็อกพอร์ต 7860 เปิดผ่านลิงก์ CloudFront แทน |
| ไม่ได้อีเมลเตือน/สรุป | SNS → Subscriptions ต้อง Confirmed / ดู Junk / อีเมลมหาวิทยาลัยอาจไปแท็บ Other |
| เว็บขึ้นแต่ไม่บันทึก ("บันทึกผลนี้ไม่ครบ") | EC2 ไม่ได้ใช้ LabInstanceProfile หรือ RDS ยังไม่ available ดู `sudo journalctl -u khadsan -n 50` |
| CloudFront 502 / 504 | เว็บบน EC2 ยังไม่ขึ้น หรือเพิ่ง Start Lab ใหม่ → `python3 aws/fix_origin.py` |

## เรื่องความปลอดภัยที่ควรรู้

- bucket ปิด public ทั้งหมด หน้า /history เปิดรูปผ่านลิงก์ชั่วคราว 1 ชั่วโมง
- RDS ไม่เปิดสาธารณะ รับเฉพาะจาก `khadsan-web-sg` และเว็บต่อแบบเข้ารหัส (TLS)
- ไม่มี Access Key ในโค้ด สิทธิ์มาจาก LabRole ของ EC2 / Lambda
- `~/khadsan.env` และ `~/khadsan-userdata.sh` มีรหัส DB ห้ามแชร์ / ห้ามใส่ในสไลด์ / ห้าม commit ขึ้น GitHub
- พอร์ต 7860 เปิดให้ทุกคนเพื่อทดสอบ ถ้าอยากให้เข้าทาง CloudFront อย่างเดียว ให้แก้ inbound rule ของ `khadsan-web-sg` เป็น prefix list `com.amazonaws.global.cloudfront.origin-facing`
