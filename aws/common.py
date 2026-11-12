# ชื่อทรัพยากรและค่าที่สคริปต์ใน aws/ ใช้ร่วมกัน (รันใน AWS CloudShell ซึ่งมี boto3 ให้แล้ว)
# ใช้กับ AWS Academy Learner Lab : สร้าง IAM role เองไม่ได้ ใช้ LabRole / LabInstanceProfile ที่ Lab มีให้
import os
import sys

REGION = "us-east-1"

LAB_ROLE = "LabRole"                   # role ของ Learner Lab : ใช้ทั้ง EC2 และ Lambda
EC2_PROFILE = "LabInstanceProfile"     # instance profile ที่ผูกกับ LabRole (เลือกตอน Launch EC2)
LAMBDA_ROLE = LAB_ROLE
WEB_SG = "khadsan-web-sg"              # เปิดพอร์ต 7860
DB_SG = "khadsan-db-sg"                # MySQL 3306 เฉพาะจาก khadsan-web-sg
DB_ID = "khadsan-db"
DB_NAME = "khadsan"
DB_USER = "admin"
BUCKET_PREFIX = "khadsan-images-"
TOPIC = "khadsan-alerts"
LAMBDA = "KhadsanDailySummary"
RULE = "khadsan-daily-1800"
CRON = "cron(0 11 * * ? *)"            # 11:00 UTC = 18:00 เวลาไทย
EC2_PREFIX = "khadsan-web"
CF_COMMENT = "khadsan-ai"              # ใส่ใน Description ของ CloudFront ให้ check/cleanup หาเจอ
PORT = 7860

# ค่าที่สคริปต์ขั้น 1-5 จดไว้ให้สคริปต์อื่นใช้ (มีรหัส DB อยู่ข้างใน อ่านได้แค่เจ้าของ)
ENV_FILE = os.path.expanduser("~/khadsan.env")


def load_env():
    values = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    values[key] = value
    return values


def save_env(values):
    old = load_env()
    old.update(values)
    fd = os.open(ENV_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("# KhadSan AI : ค่าที่ aws/step1_network_db.py จดไว้ ห้ามแชร์ไฟล์นี้ (มีรหัสฐานข้อมูล)\n")
        for key, value in old.items():
            f.write(key + "=" + value + "\n")
    os.chmod(ENV_FILE, 0o600)


def session():
    import boto3
    s = boto3.session.Session(region_name=REGION)
    if s.region_name != REGION:
        sys.exit("ต้องใช้ region " + REGION)
    return s


def account_id(s):
    return s.client("sts").get_caller_identity()["Account"]


def default_vpc(ec2):
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"]
    if not vpcs:
        sys.exit("ไม่พบ default VPC ใน " + REGION + " (บัญชีใหม่จะมีให้อยู่แล้ว ถ้าลบไปให้สร้างใหม่ที่ VPC → Actions → Create default VPC)")
    return vpcs[0]["VpcId"]


def find_sg(ec2, name, vpc_id):
    found = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [name]},
                                                  {"Name": "vpc-id", "Values": [vpc_id]}])["SecurityGroups"]
    return found[0] if found else None


def find_buckets(s3):
    return [b["Name"] for b in s3.list_buckets().get("Buckets", []) if b["Name"] == BUCKET_PREFIX.rstrip("-") or b["Name"].startswith(BUCKET_PREFIX)]


def find_topic_arn(sns):
    for page in sns.get_paginator("list_topics").paginate():
        for t in page["Topics"]:
            if t["TopicArn"].endswith(":" + TOPIC):
                return t["TopicArn"]
    return None


def list_cloudfront(cf):
    """คืน (รายการ distribution, None) หรือ (None, ข้อความ) ถ้าบัญชีไม่มีสิทธิ์ CloudFront (Learner Lab บางรุ่นปิดไว้)"""
    try:
        return cf.list_distributions().get("DistributionList", {}).get("Items", []), None
    except Exception as e:   # noqa: BLE001
        if "AccessDenied" in type(e).__name__ or "AccessDenied" in str(e) or "not authorized" in str(e):
            return None, "บัญชีนี้ไม่มีสิทธิ์ใช้ CloudFront (Learner Lab ปิดไว้)"
        raise


def pick_bucket(s3, env):
    if env.get("S3_BUCKET"):
        return env["S3_BUCKET"]
    buckets = find_buckets(s3)
    if len(buckets) == 1:
        return buckets[0]
    if not buckets:
        return None
    print("พบหลาย bucket : " + ", ".join(buckets))
    name = input("พิมพ์ชื่อ bucket ที่ใช้กับงานนี้: ").strip()
    return name if name in buckets else None
