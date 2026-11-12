# ขั้น 2 ของ workshop (รันใน AWS CloudShell) : python3 aws/step2_storage_alerts.py --email you@example.com
#   - S3 bucket ส่วนตัว khadsan-images-<เลขบัญชี> (ปิด public ทั้ง 4 ข้อ) เก็บรูปตีกรอบ + log JSON
#   - SNS topic khadsan-alerts + สมัครอีเมล (ต้องกด Confirm subscription ในอีเมลเอง)
# รันซ้ำได้ ตัวที่มีอยู่แล้วจะข้าม (มี bucket ชื่อ khadsan-images หรือ khadsan-images-* อยู่แล้วจะใช้ตัวนั้น)

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *   # noqa: F401,F403


def ensure_bucket(s3, acct, env):
    found = [env["S3_BUCKET"]] if env.get("S3_BUCKET") else find_buckets(s3)
    if found:
        name = found[0]
        print("  มีอยู่แล้ว  bucket " + name)
    else:
        name = BUCKET_PREFIX + acct           # เลขบัญชีทำให้ชื่อไม่ซ้ำกับกลุ่มอื่น (ชื่อ bucket ต้องไม่ซ้ำทั้งโลก)
        s3.create_bucket(Bucket=name)         # us-east-1 ไม่ต้องใส่ LocationConstraint
        print("  สร้างแล้ว   bucket " + name)
    s3.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration={
        "BlockPublicAcls": True, "IgnorePublicAcls": True,
        "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
    print("  ปิด public access ทั้ง 4 ข้อ (รูปผู้ใช้เป็นส่วนตัว เว็บเปิดผ่านลิงก์ชั่วคราว)")
    return name


def ensure_topic(sns, email):
    arn = sns.create_topic(Name=TOPIC)["TopicArn"]   # มีอยู่แล้วจะได้ ARN เดิม
    print("  topic " + arn)
    subs = sns.list_subscriptions_by_topic(TopicArn=arn)["Subscriptions"]
    mine = [x for x in subs if x["Protocol"] == "email" and x["Endpoint"].lower() == email.lower()]
    if mine:
        state = "ยืนยันแล้ว" if mine[0]["SubscriptionArn"].startswith("arn:") else "รอกด Confirm ในอีเมล"
        print("  อีเมล " + email + " สมัครไว้แล้ว (" + state + ")")
    else:
        sns.subscribe(TopicArn=arn, Protocol="email", Endpoint=email)
        print("  ส่งอีเมลยืนยันไปที่ " + email + " แล้ว")
    return arn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", help="อีเมลที่รับแจ้งเตือน")
    args = ap.parse_args()
    email = (args.email or input("อีเมลที่รับแจ้งเตือน: ")).strip()
    if "@" not in email:
        sys.exit("อีเมลไม่ถูกต้อง")

    s = session()
    acct = account_id(s)
    env = load_env()
    print("บัญชี " + acct + " / region " + REGION)

    print("\n[1/2] S3")
    bucket = ensure_bucket(s.client("s3"), acct, env)
    print("\n[2/2] SNS")
    arn = ensure_topic(s.client("sns"), email)

    save_env({"ACCOUNT_ID": acct, "S3_BUCKET": bucket, "SNS_TOPIC_ARN": arn, "ALERT_EMAIL": email})
    print("\nต้องทำ : เปิดอีเมล 'AWS Notification - Subscription Confirmation' แล้วกด Confirm subscription (ดูใน Junk ด้วย)")
    print("ดูผลใน Console : S3 → Buckets → " + bucket + "  /  SNS → Topics → " + TOPIC + " → Subscriptions = Confirmed")
    print("ต่อไป → python3 aws/step3_web_server.py")


if __name__ == "__main__":
    main()
