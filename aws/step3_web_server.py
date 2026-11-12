# ขั้น 3 ของ workshop (รันใน AWS CloudShell) : python3 aws/step3_web_server.py
#   - รอ RDS พร้อม → สร้าง User data ที่ใส่ค่าครบ (userdata.py)
#   - Launch EC2 t3.small Ubuntu 24.04 ดิสก์ EBS gp3 30 GiB, LabInstanceProfile, khadsan-web-sg, key vockey
#   - EC2 ติดตั้งเว็บเอง : git clone branch aws-workshop (เว็บ + ส่วนต่อ S3/RDS/SNS) แล้วรันด้วย gunicorn พอร์ต 7860
# ไม่ต้องคัดลอก User data ไปวางเอง (เคยพังเพราะบรรทัดถูกตัดตอนคัดลอกจากสไลด์)
#
# ตัวเลือก
#   --alert N     คัดออกตั้งแต่ N ลูกในรูปเดียวส่งอีเมลเตือน (ไม่ใส่ = 3)
#   --replace     มี EC2 khadsan-web-* อยู่แล้ว : สร้างตัวใหม่ แล้ว Terminate ตัวเก่า
#   --zip         ไม่ใช้ GitHub ส่งโฟลเดอร์ web/ ใน CloudShell ผ่าน S3 แทน

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *   # noqa: F401,F403
import userdata

INSTANCE_TYPE = "t3.small"      # PyTorch กินแรม ใช้ 2 GB + swap 4 GB
DISK_GB = 30
KEY_NAME = "vockey"             # key pair ที่ Learner Lab มีให้
UBUNTU_SSM = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"


def find_ami(s):
    try:
        return s.client("ssm").get_parameter(Name=UBUNTU_SSM)["Parameter"]["Value"]
    except Exception:   # noqa: BLE001  อ่าน SSM ไม่ได้ → หาเองจาก Canonical
        imgs = s.client("ec2").describe_images(Owners=["099720109477"], Filters=[
            {"Name": "name", "Values": ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]},
            {"Name": "state", "Values": ["available"]}])["Images"]
        if not imgs:
            sys.exit("หา AMI Ubuntu 24.04 ไม่เจอ")
        return max(imgs, key=lambda i: i["CreationDate"])["ImageId"]


def running_web(ec2):
    res = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [EC2_PREFIX + "*"]},
                                          {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]}])
    return [i for r in res["Reservations"] for i in r["Instances"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alert", type=int, default=3)
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--zip", action="store_true")
    args = ap.parse_args()

    s = session()
    ec2 = s.client("ec2")
    old = running_web(ec2)
    if old and not args.replace:
        for i in old:
            print("มี EC2 อยู่แล้ว : " + i["InstanceId"] + " (" + i["State"]["Name"] + ") " + i.get("PublicDnsName", ""))
        sys.exit("ถ้าจะสร้างใหม่แทนตัวเดิม ให้รัน : python3 aws/step3_web_server.py --replace")

    print("[1/3] สร้าง User data")
    script, endpoint, bucket = userdata.build(s, alert=args.alert, use_zip=args.zip)

    print("\n[2/3] Launch EC2")
    sg = find_sg(ec2, WEB_SG, default_vpc(ec2))
    if not sg:
        sys.exit("ไม่พบ security group " + WEB_SG + " ให้รัน python3 aws/step1_network_db.py ก่อน")
    ami = find_ami(s)
    name = EC2_PREFIX + "-" + time.strftime("%m%d-%H%M")
    inst = ec2.run_instances(
        ImageId=ami, InstanceType=INSTANCE_TYPE, MinCount=1, MaxCount=1, KeyName=KEY_NAME,
        SecurityGroupIds=[sg["GroupId"]], IamInstanceProfile={"Name": EC2_PROFILE},
        BlockDeviceMappings=[{"DeviceName": "/dev/sda1",
                              "Ebs": {"VolumeSize": DISK_GB, "VolumeType": "gp3", "DeleteOnTermination": True}}],
        UserData=script,
        TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": name}]},
                           {"ResourceType": "volume", "Tags": [{"Key": "Name", "Value": name + "-ebs"}]}],
    )["Instances"][0]
    iid = inst["InstanceId"]
    print("  สร้างแล้ว " + name + " (" + iid + ") AMI " + ami)
    ec2.get_waiter("instance_running").wait(InstanceIds=[iid])
    dns = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0].get("PublicDnsName", "")
    save_env({"EC2_ID": iid, "EC2_DNS": dns})

    print("\n[3/3] เครื่องเก่า")
    if old:
        ec2.terminate_instances(InstanceIds=[i["InstanceId"] for i in old])
        print("  สั่ง Terminate " + ", ".join(i["InstanceId"] for i in old))
    else:
        print("  ไม่มี")

    print("\nต้องเห็น : EC2 " + name + " สถานะ Running (Console → EC2 → Instances)")
    print("เครื่องกำลังติดตั้งเว็บเอง ราว 10-15 นาที (ลง PyTorch) ระหว่างรอ ทำขั้น 4 ได้เลย")
    print("เช็กว่าเสร็จ : curl -s -o /dev/null -w '%{http_code}\\n' http://" + dns + ":" + str(PORT) + "/   (ได้ 200 = เสร็จ)")
    print("ต่อไป → python3 aws/step4_automation.py")


if __name__ == "__main__":
    main()
