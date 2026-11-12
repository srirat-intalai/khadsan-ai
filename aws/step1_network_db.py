# ขั้น 1 ของ workshop (รันใน AWS CloudShell ของ Learner Lab) : python3 aws/step1_network_db.py
#   - ตรวจว่ามี LabRole / LabInstanceProfile (Learner Lab สร้าง role เองไม่ได้)
#   - Security Group 2 ตัว : khadsan-web-sg (7860) และ khadsan-db-sg (3306 เฉพาะจาก web-sg)
#   - สั่งสร้าง RDS MySQL khadsan-db (ใช้เวลาราว 10 นาที ระหว่างรอให้ทำขั้นต่อไปได้เลย)
# รันซ้ำได้ ตัวที่มีอยู่แล้วจะข้าม
# จดค่าไว้ใน ~/khadsan.env (มีรหัส DB อ่านได้แค่เจ้าของ) ให้สคริปต์ขั้นต่อไปใช้

import os
import sys
import time
import getpass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *   # noqa: F401,F403


def check_lab_role(iam):
    # Learner Lab : อ่าน IAM ได้ แต่สร้าง role ไม่ได้ เลยแค่ตรวจว่ามี LabRole / LabInstanceProfile
    for kind, fn in (("role " + LAB_ROLE, lambda: iam.get_role(RoleName=LAB_ROLE)),
                     ("instance profile " + EC2_PROFILE, lambda: iam.get_instance_profile(InstanceProfileName=EC2_PROFILE))):
        try:
            fn()
            print("  พบแล้ว     " + kind)
        except Exception as e:   # noqa: BLE001
            if "NoSuchEntity" in type(e).__name__ or "NoSuchEntity" in str(e):
                print("  ไม่พบ      " + kind + " (ต้องใช้บัญชี AWS Academy Learner Lab)")
            else:
                print("  อ่านไม่ได้ " + kind + " (" + type(e).__name__ + ") ข้ามได้ ใช้ชื่อนี้ตอนเลือกใน Console")


def ensure_sg(ec2, name, desc, vpc_id):
    sg = find_sg(ec2, name, vpc_id)
    if sg:
        print("  มีอยู่แล้ว  security group " + name + " (" + sg["GroupId"] + ")")
        return sg["GroupId"]
    gid = ec2.create_security_group(GroupName=name, Description=desc, VpcId=vpc_id,
                                    TagSpecifications=[{"ResourceType": "security-group",
                                                        "Tags": [{"Key": "Name", "Value": name}]}])["GroupId"]
    print("  สร้างแล้ว   security group " + name + " (" + gid + ")")
    return gid


def add_rule(ec2, gid, perm):
    try:
        ec2.authorize_security_group_ingress(GroupId=gid, IpPermissions=[perm])
    except ec2.exceptions.ClientError as e:
        if "InvalidPermission.Duplicate" not in str(e):
            raise


def ask_password():
    env_pw = os.environ.get("KHADSAN_DB_PASSWORD")
    if env_pw:
        return env_pw
    print("\nตั้งรหัสผ่านฐานข้อมูล (8-41 ตัว ห้ามมี / @ \" ' \\ และช่องว่าง) พิมพ์แล้วจะไม่ขึ้นบนจอ")
    while True:
        pw = getpass.getpass("  รหัสผ่าน DB: ")
        bad = [c for c in "/@\"'\\ " if c in pw]
        if not 8 <= len(pw) <= 41 or bad:
            print("  ใช้ไม่ได้ ลองใหม่")
            continue
        if getpass.getpass("  พิมพ์ซ้ำ:    ") != pw:
            print("  ไม่ตรงกัน ลองใหม่")
            continue
        return pw


def main():
    s = session()
    acct = account_id(s)
    print("บัญชี " + acct + " / region " + REGION)
    iam, ec2, rds = s.client("iam"), s.client("ec2"), s.client("rds")

    print("\n[1/3] IAM (LabRole)")
    check_lab_role(iam)

    print("\n[2/3] Security Group")
    vpc_id = default_vpc(ec2)
    web = ensure_sg(ec2, WEB_SG, "KhadSan AI web (Flask port 7860)", vpc_id)
    add_rule(ec2, web, {"IpProtocol": "tcp", "FromPort": PORT, "ToPort": PORT,
                        "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "workshop: web 7860"}]})
    db = ensure_sg(ec2, DB_SG, "KhadSan AI MySQL from web only", vpc_id)
    add_rule(ec2, db, {"IpProtocol": "tcp", "FromPort": 3306, "ToPort": 3306,
                       "UserIdGroupPairs": [{"GroupId": web, "Description": "MySQL from khadsan-web-sg"}]})

    print("\n[3/3] RDS MySQL " + DB_ID)
    env = load_env()
    try:
        status = rds.describe_db_instances(DBInstanceIdentifier=DB_ID)["DBInstances"][0]["DBInstanceStatus"]
        print("  มีอยู่แล้ว  สถานะ " + status)
        if "DB_PASSWORD" not in env:
            print("  ไม่พบรหัส DB ใน " + ENV_FILE + " ถ้าจำรหัสได้ ให้รันใหม่ด้วย KHADSAN_DB_PASSWORD='รหัส' python3 aws/step1_network_db.py")
            if os.environ.get("KHADSAN_DB_PASSWORD"):
                save_env({"DB_PASSWORD": os.environ["KHADSAN_DB_PASSWORD"]})
    except rds.exceptions.DBInstanceNotFoundFault:
        pw = ask_password()
        rds.create_db_instance(
            DBInstanceIdentifier=DB_ID, Engine="mysql", EngineVersion="8.4",
            EngineLifecycleSupport="open-source-rds-extended-support-disabled",
            DBInstanceClass="db.t4g.micro", AllocatedStorage=20, StorageType="gp2",
            MasterUsername=DB_USER, MasterUserPassword=pw, DBName=DB_NAME,
            VpcSecurityGroupIds=[db], PubliclyAccessible=False, MultiAZ=False,
            StorageEncrypted=True, BackupRetentionPeriod=0, DeletionProtection=False,
            Tags=[{"Key": "project", "Value": "khadsan-ai"}])
        save_env({"DB_PASSWORD": pw})
        print("  สั่งสร้างแล้ว (ราว 10 นาที) ทำขั้นต่อไปได้เลย ไม่ต้องรอ")

    save_env({"ACCOUNT_ID": acct, "DB_USER": DB_USER, "DB_NAME": DB_NAME, "WEB_SG_ID": web, "DB_SG_ID": db})
    print("\nต้องเห็น : พบ LabRole, security group 2 ตัว และ RDS khadsan-db สถานะ creating หรือ available")
    print("จดค่าไว้ที่ " + ENV_FILE + " แล้ว (ห้ามแชร์)")
    print("ดูผลใน Console : Search → RDS → Databases → khadsan-db (Creating)  /  EC2 → Security Groups")
    print("ต่อไป (ไม่ต้องรอ RDS) → python3 aws/step2_storage_alerts.py")


if __name__ == "__main__":
    t = time.time()
    main()
    print("ใช้เวลา %.0f วินาที" % (time.time() - t))
