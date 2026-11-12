# ใช้หลัง Start Lab ใหม่ (รันใน AWS CloudShell) : python3 aws/fix_origin.py
# Learner Lab หยุด EC2 ตอนจบ session พอเปิดใหม่ EC2 ได้ Public DNS ใหม่ แต่ CloudFront ยังชี้ที่เดิม (ขึ้น 502/504)
# สคริปต์นี้ : เปิด EC2/RDS ที่หยุดอยู่ → รอพร้อม → แก้ origin ของ CloudFront ให้เป็น Public DNS ใหม่

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *   # noqa: F401,F403


def main():
    s = session()
    ec2, rds, cf = s.client("ec2"), s.client("rds"), s.client("cloudfront")

    res = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [EC2_PREFIX + "*"]},
                                          {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]}])
    inst = [i for r in res["Reservations"] for i in r["Instances"]]
    if not inst:
        sys.exit("ไม่พบ EC2 ชื่อขึ้นต้น " + EC2_PREFIX)
    i = inst[0]
    if i["State"]["Name"] in ("stopped", "stopping"):
        if i["State"]["Name"] == "stopping":
            ec2.get_waiter("instance_stopped").wait(InstanceIds=[i["InstanceId"]])
        ec2.start_instances(InstanceIds=[i["InstanceId"]])
        print("สั่งเปิด EC2 " + i["InstanceId"])
    ec2.get_waiter("instance_running").wait(InstanceIds=[i["InstanceId"]])
    dns = ec2.describe_instances(InstanceIds=[i["InstanceId"]])["Reservations"][0]["Instances"][0].get("PublicDnsName")
    if not dns:
        sys.exit("EC2 ไม่มี Public DNS (ตอน Launch ต้องเปิด Auto-assign public IP)")
    print("EC2 Public DNS ตอนนี้ : " + dns)

    try:
        db = rds.describe_db_instances(DBInstanceIdentifier=DB_ID)["DBInstances"][0]
        if db["DBInstanceStatus"] == "stopped":
            rds.start_db_instance(DBInstanceIdentifier=DB_ID)
            print("สั่งเปิด RDS " + DB_ID + " (ราว 5 นาที เว็บจะบันทึกประวัติได้เมื่อ available)")
    except Exception as e:   # noqa: BLE001
        print("ตรวจ RDS ไม่ได้ : " + type(e).__name__)

    dists, denied = list_cloudfront(cf)
    if denied:
        print("ข้าม CloudFront : " + denied)
        print("เปิดเว็บที่ http://" + dns + ":" + str(PORT) + "/ (เครื่องเปิดเว็บเองราว 1-2 นาทีหลังเครื่องขึ้น)")
        return
    mine = [d for d in dists if d.get("Comment") == CF_COMMENT]
    if not mine:
        sys.exit("ไม่พบ CloudFront ที่ Description = " + CF_COMMENT)
    for d in mine:
        conf = cf.get_distribution_config(Id=d["Id"])
        config = conf["DistributionConfig"]
        origin = config["Origins"]["Items"][0]
        if origin["DomainName"] == dns:
            print("CloudFront " + d["Id"] + " ชี้ถูกอยู่แล้ว : https://" + d["DomainName"])
            continue
        print("แก้ origin " + origin["DomainName"] + " → " + dns)
        origin["DomainName"] = dns
        cf.update_distribution(Id=d["Id"], IfMatch=conf["ETag"], DistributionConfig=config)
        print("ต้องเห็น : CloudFront " + d["Id"] + " สถานะ Deploying แล้วกลับเป็น Deployed (ราว 5 นาที) แล้วเปิด https://" + d["DomainName"])
    print("เว็บบน EC2 เปิดเองหลังเครื่องขึ้น (systemd) ราว 1-2 นาที")


if __name__ == "__main__":
    main()
