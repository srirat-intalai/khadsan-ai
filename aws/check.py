# ขั้น 7 ของ workshop (รันใน AWS CloudShell) : python3 aws/check.py
# ตรวจงานทุกบริการ ขึ้น ✅ / ❌ พร้อมบอกว่าต้องแก้อะไร (อ่านอย่างเดียว ไม่แก้อะไรในบัญชี)

import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *   # noqa: F401,F403

results = []


def check(name, ok, hint=""):
    results.append(ok)
    print(("✅ " if ok else "❌ ") + name + ("" if ok or not hint else "\n     → " + hint))
    return ok


def safe(fn, default=None):
    try:
        return fn()
    except Exception as e:   # noqa: BLE001
        text = type(e).__name__ + " " + str(e)
        if "NotFound" not in text and "NoSuch" not in text:   # ไม่พบ = ยังไม่ได้สร้าง บรรทัด ❌ บอกอยู่แล้ว
            print("   (อ่านไม่ได้: " + type(e).__name__ + ")")
        return default


def http_status(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "khadsan-check"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:   # noqa: BLE001
        return None


def cost_this_month(s):
    # Cost Explorer (ข้อมูลเดียวกับ Cost & Usage Report) Learner Lab อาจไม่ให้อ่าน → คืน None
    import datetime
    try:
        today = datetime.date.today()
        start = today.replace(day=1)
        end = today + datetime.timedelta(days=1)
        r = s.client("ce", region_name="us-east-1").get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="MONTHLY", Metrics=["UnblendedCost"])
        amt = r["ResultsByTime"][0]["Total"]["UnblendedCost"]
        return "%.2f %s (ตั้งแต่ %s)" % (float(amt["Amount"]), amt["Unit"], start.isoformat())
    except Exception:   # noqa: BLE001
        return None


def main():
    s = session()
    env = load_env()
    iam, ec2, rds, s3 = s.client("iam"), s.client("ec2"), s.client("rds"), s.client("s3")
    sns, lam, events = s.client("sns"), s.client("lambda"), s.client("events")
    print("บัญชี " + account_id(s) + " / region " + REGION + "\n")

    print("— บริการพื้นฐานที่ทุกระบบต้องมี (สีม่วง : ไม่นับในเกณฑ์ 4 บริการ) : IAM / VPC")
    check("IAM role " + LAB_ROLE + " (Learner Lab)", safe(lambda: bool(iam.get_role(RoleName=LAB_ROLE)), False),
          "ต้องใช้บัญชี AWS Academy Learner Lab และกด Start Lab ก่อน")
    vpc = safe(lambda: default_vpc(ec2))
    web = find_sg(ec2, WEB_SG, vpc) if vpc else None
    db_sg = find_sg(ec2, DB_SG, vpc) if vpc else None
    check("Security group " + WEB_SG + " เปิด " + str(PORT),
          bool(web) and any(p.get("FromPort") == PORT for p in web["IpPermissions"]), "รัน python3 aws/step1_network_db.py")
    db_ok = bool(db_sg) and bool(web) and any(
        p.get("FromPort") == 3306 and any(g["GroupId"] == web["GroupId"] for g in p.get("UserIdGroupPairs", []))
        for p in db_sg["IpPermissions"])
    check("Security group " + DB_SG + " รับ 3306 จาก " + WEB_SG + " เท่านั้น", db_ok, "รัน python3 aws/step1_network_db.py")

    print("\n— บริการที่นับคะแนน 7 ตัว : EC2, EBS, S3, RDS, SNS, Lambda, EventBridge")
    # RDS
    db = safe(lambda: rds.describe_db_instances(DBInstanceIdentifier=DB_ID)["DBInstances"][0])
    check("RDS " + DB_ID + " สถานะ available", bool(db) and db["DBInstanceStatus"] == "available",
          "สถานะตอนนี้ " + (db["DBInstanceStatus"] if db else "ไม่พบ") + " (สร้างใหม่ใช้ราว 10 นาที)")
    if db:
        check("RDS ไม่เปิดสาธารณะ", not db["PubliclyAccessible"], "Modify → Public access = No")

    # S3
    bucket = env.get("S3_BUCKET") or (find_buckets(s3) or [None])[0]
    check("S3 bucket " + (bucket or BUCKET_PREFIX + "..."), bool(bucket), "รัน python3 aws/step2_storage_alerts.py")
    if bucket:
        pab = safe(lambda: s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"], {})
        check("S3 Block all public access", bool(pab) and all(pab.values()), "Permissions → Block public access → เปิดทั้ง 4 ข้อ")
        for prefix, hint in (("images/", "ยังไม่มีรูป ลองสแกนผลไม้ผ่านเว็บ 1 รูป"),
                             ("logs/", "ยังไม่มี log ลองสแกนผลไม้ผ่านเว็บ 1 รูป")):
            n = safe(lambda: s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=50).get("KeyCount", 0), 0)
            check("S3 มีไฟล์ใน " + prefix + " (" + str(n) + " ไฟล์ ไม่นับโฟลเดอร์)",
                  n > 1 or (n == 1 and not safe(lambda: s3.head_object(Bucket=bucket, Key=prefix), False)), hint)

    # SNS
    topic = find_topic_arn(sns)
    check("SNS topic " + TOPIC, bool(topic), "รัน python3 aws/step2_storage_alerts.py")
    if topic:
        subs = safe(lambda: sns.list_subscriptions_by_topic(TopicArn=topic)["Subscriptions"], [])
        confirmed = [x for x in subs if x["Protocol"] == "email" and x["SubscriptionArn"].startswith("arn:")]
        check("SNS email subscription ยืนยันแล้ว (" + str(len(confirmed)) + ")", bool(confirmed),
              "เปิดอีเมลจาก AWS Notifications แล้วกด Confirm subscription")

    # Lambda
    fn = safe(lambda: lam.get_function(FunctionName=LAMBDA)["Configuration"])
    check("Lambda " + LAMBDA, bool(fn), "รัน python3 aws/step4_automation.py")
    if fn:
        check("Lambda ใช้ role " + LAMBDA_ROLE, fn["Role"].endswith("/" + LAMBDA_ROLE), "รัน python3 aws/step4_automation.py")
        variables = fn.get("Environment", {}).get("Variables", {})
        check("Lambda มี S3_BUCKET และ SNS_TOPIC_ARN",
              variables.get("S3_BUCKET") == bucket and variables.get("SNS_TOPIC_ARN") == topic,
              "Configuration → Environment variables ให้ตรงกับ bucket / topic ของตัวเอง")

    # EventBridge
    rule = safe(lambda: events.describe_rule(Name=RULE))
    check("EventBridge rule " + RULE + " เปิดอยู่ และตั้ง " + CRON,
          bool(rule) and rule["State"] == "ENABLED" and rule.get("ScheduleExpression") == CRON,
          "รัน python3 aws/step4_automation.py")
    if rule:
        targets = safe(lambda: events.list_targets_by_rule(Rule=RULE)["Targets"], [])
        check("EventBridge target = Lambda " + LAMBDA, any(t["Arn"].endswith(":function:" + LAMBDA) for t in targets),
              "รัน python3 aws/step4_automation.py")

    # EC2 + EBS
    res = safe(lambda: ec2.describe_instances(Filters=[
        {"Name": "tag:Name", "Values": [EC2_PREFIX + "*"]},
        {"Name": "instance-state-name", "Values": ["running"]}])["Reservations"], [])
    inst = sorted([i for r in res for i in r["Instances"]], key=lambda i: i["LaunchTime"], reverse=True)   # ตัวล่าสุดก่อน
    check("EC2 " + EC2_PREFIX + "-* กำลังรัน", bool(inst), "รัน python3 aws/step3_web_server.py")
    dns = None
    if inst:
        i = inst[0]
        dns = i.get("PublicDnsName")
        check("EC2 ใช้ IAM profile " + EC2_PROFILE, EC2_PROFILE in i.get("IamInstanceProfile", {}).get("Arn", ""),
              "Actions → Security → Modify IAM role → " + EC2_PROFILE)
        check("EC2 ใช้ security group " + WEB_SG, any(g["GroupName"] == WEB_SG for g in i["SecurityGroups"]),
              "Actions → Security → Change security groups")
        vols = [m["Ebs"]["VolumeId"] for m in i.get("BlockDeviceMappings", []) if "Ebs" in m]
        vol = safe(lambda: ec2.describe_volumes(VolumeIds=vols)["Volumes"][0]) if vols else None
        check("EBS root volume ต่ออยู่" + (" (" + vol["VolumeType"] + " " + str(vol["Size"]) + " GiB)" if vol else ""),
              bool(vol) and vol["State"] == "in-use")
        if dns:
            code = http_status("http://" + dns + ":" + str(PORT) + "/")
            check("เว็บบน EC2 ตอบ http://" + dns + ":" + str(PORT) + " (" + str(code) + ")", code == 200,
                  "รอติดตั้งราว 10 นาที แล้วดู sudo tail -n 40 /var/log/khadsan-setup.log บน EC2")

    # บริการพื้นฐาน : CloudWatch (log) / Cost (เครดิต) / CLI (สคริปต์นี้ก็คือ CLI)
    print("\n— บริการพื้นฐาน (สีม่วง) : CloudWatch / CLI / Cost")
    logs = s.client("logs")
    group = "/aws/lambda/" + LAMBDA
    streams = safe(lambda: logs.describe_log_streams(logGroupName=group, orderBy="LastEventTime",
                                                     descending=True, limit=1)["logStreams"], [])
    check("CloudWatch มี log ของ Lambda (" + group + ")", bool(streams),
          "รัน Lambda 1 ครั้ง (step4 หรือกด Test) แล้วเปิด CloudWatch → Logs → Log Management → " + group)
    print("ℹ️  CLI : คำสั่ง aws ... และสคริปต์ใน aws/ ที่รันอยู่นี้")
    cost = cost_this_month(s)
    print("ℹ️  ค่าใช้จ่ายเดือนนี้ : " + cost if cost else
          "ℹ️  ค่าใช้จ่าย : ดูที่หน้า Learner Lab (Used $ / Budget) (บัญชีนี้อ่าน Cost Explorer ไม่ได้)")

    passed = sum(results)
    print("\nผ่าน " + str(passed) + "/" + str(len(results)) + (" 🎉 ครบทุกข้อ" if passed == len(results) else ""))
    print("ทดสอบด้วยมือเพิ่ม : เปิด http://" + str(dns) + ":" + str(PORT) + "/ → ปุ่มอัปโหลด/ถ่ายรูป → ดูหน้า /history → ดูอีเมลเตือน")


if __name__ == "__main__":
    main()
