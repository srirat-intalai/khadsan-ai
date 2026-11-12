# ขั้น 8 ของ workshop (รันใน AWS CloudShell) : python3 aws/cleanup.py
# ลบทุกอย่างที่ workshop สร้าง (End Lab แค่หยุดเครื่อง ไม่ลบ ทรัพยากรที่ค้างยังกินเครดิต Lab)
# แสดงรายการก่อน แล้วต้องพิมพ์ DELETE ถึงจะลบจริง
#
# ตัวเลือก
#   --yes        ไม่ถามยืนยัน
#   --no-wait    CloudFront แค่สั่ง Disable ไม่รอลบ (ลบเองทีหลังได้ หรือรันสคริปต์นี้ซ้ำ)
# CloudFront ต้อง Disable แล้วรอสถานะ Deployed (ราว 5-15 นาที) ก่อนถึงจะลบได้ สคริปต์จะรอให้

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *   # noqa: F401,F403


def step(msg):
    print("\n• " + msg)


def quiet(fn, what):
    try:
        fn()
        print("  ลบแล้ว  " + what)
    except Exception as e:   # noqa: BLE001
        name = type(e).__name__
        if "NotFound" in name or "NoSuchEntity" in name or "NoSuchBucket" in name or "NotFound" in str(e):
            print("  ไม่มีแล้ว " + what)
        else:
            print("  ลบไม่ได้ " + what + " : " + str(e))


def find_all(s):
    ec2, cf, s3 = s.client("ec2"), s.client("cloudfront"), s.client("s3")
    res = ec2.describe_instances(Filters=[
        {"Name": "tag:Name", "Values": [EC2_PREFIX + "*"]},
        {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]}])["Reservations"]
    instances = [i for r in res for i in r["Instances"]]
    dns = {i.get("PublicDnsName") for i in instances if i.get("PublicDnsName")}
    dists, denied = list_cloudfront(cf)
    if denied:
        print("ข้าม CloudFront : " + denied)
        dists = []
    mine = [d for d in dists if d.get("Comment") == CF_COMMENT or
            any(o["DomainName"] in dns for o in d["Origins"]["Items"])]
    return instances, mine, find_buckets(s3)


def delete_cloudfront(cf, dist_id, wait):
    conf = cf.get_distribution_config(Id=dist_id)
    etag, config = conf["ETag"], conf["DistributionConfig"]
    if config["Enabled"]:
        config["Enabled"] = False
        etag = cf.update_distribution(Id=dist_id, IfMatch=etag, DistributionConfig=config)["ETag"]
        print("  สั่ง Disable แล้ว " + dist_id)
    if not wait:
        print("  ยังไม่ลบ " + dist_id + " (--no-wait) รอสถานะ Deployed แล้วกด Delete เอง หรือรันสคริปต์นี้ซ้ำ")
        return
    print("  รอ " + dist_id + " Deployed (ราว 5-15 นาที) ...")
    cf.get_waiter("distribution_deployed").wait(Id=dist_id, WaiterConfig={"Delay": 30, "MaxAttempts": 60})
    etag = cf.get_distribution_config(Id=dist_id)["ETag"]
    cf.delete_distribution(Id=dist_id, IfMatch=etag)
    print("  ลบแล้ว  CloudFront " + dist_id)


def empty_and_delete_bucket(s3, name):
    pages = s3.get_paginator("list_object_versions").paginate(Bucket=name)
    for page in pages:
        items = [{"Key": v["Key"], "VersionId": v["VersionId"]}
                 for v in page.get("Versions", []) + page.get("DeleteMarkers", [])]
        for i in range(0, len(items), 1000):
            s3.delete_objects(Bucket=name, Delete={"Objects": items[i:i + 1000], "Quiet": True})
    s3.delete_bucket(Bucket=name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--no-wait", action="store_true")
    args = ap.parse_args()

    s = session()
    print("บัญชี " + account_id(s) + " / region " + REGION)
    instances, dists, buckets = find_all(s)

    print("\nจะลบสิ่งเหล่านี้ (ไม่มีก็ข้าม)")
    print("  EventBridge rule " + RULE + " / Lambda " + LAMBDA + " + log group")
    print("  CloudFront : " + (", ".join(d["Id"] + " (" + d["DomainName"] + ")" for d in dists) or "ไม่พบ"))
    print("  EC2 : " + (", ".join(i["InstanceId"] for i in instances) or "ไม่พบ") + " (EBS root ลบตามไปด้วย)")
    print("  RDS " + DB_ID + " (ไม่เก็บ snapshot)")
    print("  S3 : " + (", ".join(buckets) or "ไม่พบ") + " (ลบรูปและ log ทั้งหมดในนั้น)")
    print("  SNS topic " + TOPIC + " / Security group " + DB_SG + ", " + WEB_SG)
    print("  ไฟล์ " + ENV_FILE + " และ ~/khadsan-userdata.sh (LabRole ของ Lab ไม่ลบ)")
    if not args.yes and input("\nพิมพ์ DELETE เพื่อลบจริง: ").strip() != "DELETE":
        sys.exit("ยกเลิก ไม่ได้ลบอะไร")

    ec2, rds, s3 = s.client("ec2"), s.client("rds"), s.client("s3")
    events, lam, sns, cf, logs = (s.client("events"), s.client("lambda"), s.client("sns"),
                                  s.client("cloudfront"), s.client("logs"))

    step("EventBridge + Lambda")
    try:
        ids = [t["Id"] for t in events.list_targets_by_rule(Rule=RULE)["Targets"]]
        if ids:
            events.remove_targets(Rule=RULE, Ids=ids)
    except Exception:   # noqa: BLE001
        pass
    quiet(lambda: events.delete_rule(Name=RULE), "EventBridge rule " + RULE)
    quiet(lambda: lam.delete_function(FunctionName=LAMBDA), "Lambda " + LAMBDA)
    quiet(lambda: logs.delete_log_group(logGroupName="/aws/lambda/" + LAMBDA), "CloudWatch log group ของ Lambda")

    step("EC2 + RDS (สั่งลบพร้อมกัน แล้วค่อยรอ)")
    ids = [i["InstanceId"] for i in instances]
    if ids:
        ec2.terminate_instances(InstanceIds=ids)
        print("  สั่ง Terminate แล้ว " + ", ".join(ids))
    db_exists = True
    try:
        rds.delete_db_instance(DBInstanceIdentifier=DB_ID, SkipFinalSnapshot=True, DeleteAutomatedBackups=True)
        print("  สั่งลบ RDS " + DB_ID + " แล้ว")
    except rds.exceptions.DBInstanceNotFoundFault:
        print("  ไม่มีแล้ว RDS " + DB_ID)
        db_exists = False
    except Exception as e:   # noqa: BLE001
        print("  ลบ RDS ไม่ได้ : " + str(e) + " (ถ้ากำลังลบอยู่แล้วก็ปกติ)")

    step("CloudFront (ต้อง Disable ก่อนลบ)")
    for d in dists:
        try:
            delete_cloudfront(cf, d["Id"], not args.no_wait)
        except Exception as e:   # noqa: BLE001
            print("  ลบ CloudFront " + d["Id"] + " ไม่ได้ : " + str(e))

    step("S3 + SNS")
    for b in buckets:
        quiet(lambda b=b: empty_and_delete_bucket(s3, b), "S3 bucket " + b)
    topic = find_topic_arn(sns)
    if topic:
        quiet(lambda: sns.delete_topic(TopicArn=topic), "SNS topic " + TOPIC + " (และ subscription)")

    step("รอ EC2 / RDS หายก่อนลบ Security group")
    if ids:
        ec2.get_waiter("instance_terminated").wait(InstanceIds=ids, WaiterConfig={"Delay": 15, "MaxAttempts": 40})
        print("  EC2 terminated แล้ว")
    if db_exists:
        print("  รอ RDS ลบเสร็จ (ราว 5-10 นาที) ...")
        try:
            rds.get_waiter("db_instance_deleted").wait(DBInstanceIdentifier=DB_ID,
                                                       WaiterConfig={"Delay": 30, "MaxAttempts": 60})
            print("  RDS ลบแล้ว")
        except Exception as e:   # noqa: BLE001
            print("  รอ RDS ไม่สำเร็จ : " + str(e))
    vpc = default_vpc(ec2)
    for name in (DB_SG, WEB_SG):   # db-sg อ้าง web-sg อยู่ ต้องลบ db-sg ก่อน
        sg = find_sg(ec2, name, vpc)
        if sg:
            quiet(lambda sg=sg: ec2.delete_security_group(GroupId=sg["GroupId"]), "security group " + name)

    step("ไฟล์ค่าลับใน CloudShell")
    for path in (ENV_FILE, os.path.expanduser("~/khadsan-userdata.sh")):
        if os.path.exists(path):
            os.remove(path)
            print("  ลบแล้ว  " + path)

    print("\nเสร็จแล้ว ต้องเห็น : EC2 terminated, RDS / S3 / CloudFront ไม่อยู่ในรายการ")
    print("ดูเครดิตที่เหลือในหน้า Learner Lab (Used $ / Budget) แล้วกด End Lab")


if __name__ == "__main__":
    main()
