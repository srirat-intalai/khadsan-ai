# ขั้น 5 ของ workshop (รันใน AWS CloudShell) : python3 aws/step5_cloudfront.py
#   - CloudFront distribution ชี้ไป EC2 (Public DNS) พอร์ต 7860 แบบ HTTP only
#   - ผู้ใช้เข้า https://xxxx.cloudfront.net (ใบรับรอง https มาให้เลย → เบราว์เซอร์ยอมเปิดกล้อง)
#   - Redirect HTTP → HTTPS, รับ POST (อัปรูป), ไม่ cache (ผลตรวจแต่ละรูปต่างกัน)
#   - Description = khadsan-ai ให้ check.py / fix_origin.py / cleanup.py หาเจอ
# มีอยู่แล้วจะไม่สร้างซ้ำ (ถ้า EC2 เปลี่ยน ใช้ python3 aws/fix_origin.py)
#
# ตัวเลือก
#   --wait    รอจนสถานะ Deployed (ราว 5-10 นาที)

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *   # noqa: F401,F403

CACHING_DISABLED = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"           # managed cache policy
ALL_VIEWER_EXCEPT_HOST = "b689b0a8-53d0-40ab-baf2-68738e2966ac"     # managed origin request policy


def web_dns(ec2):
    res = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [EC2_PREFIX + "*"]},
                                          {"Name": "instance-state-name", "Values": ["running"]}])
    inst = sorted([i for r in res["Reservations"] for i in r["Instances"]], key=lambda i: i["LaunchTime"])
    if not inst or not inst[-1].get("PublicDnsName"):
        sys.exit("ไม่พบ EC2 " + EC2_PREFIX + "-* ที่รันอยู่ ให้ทำขั้น 3 ก่อน")
    return inst[-1]["PublicDnsName"]


def config(dns):
    methods = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    return {
        "CallerReference": "khadsan-" + str(int(time.time())),
        "Comment": CF_COMMENT,
        "Enabled": True,
        "PriceClass": "PriceClass_100",
        "HttpVersion": "http2",
        "IsIPV6Enabled": True,
        "Origins": {"Quantity": 1, "Items": [{
            "Id": "khadsan-ec2", "DomainName": dns,
            "CustomOriginConfig": {"HTTPPort": PORT, "HTTPSPort": 443, "OriginProtocolPolicy": "http-only",
                                   "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]},
                                   "OriginReadTimeout": 60, "OriginKeepaliveTimeout": 5}}]},
        "DefaultCacheBehavior": {
            "TargetOriginId": "khadsan-ec2",
            "ViewerProtocolPolicy": "redirect-to-https",
            "AllowedMethods": {"Quantity": 7, "Items": methods,
                               "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]}},
            "Compress": True,
            "CachePolicyId": CACHING_DISABLED,
            "OriginRequestPolicyId": ALL_VIEWER_EXCEPT_HOST,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", action="store_true")
    args = ap.parse_args()

    s = session()
    cf, ec2 = s.client("cloudfront"), s.client("ec2")
    dns = web_dns(ec2)
    print("EC2 origin : " + dns + ":" + str(PORT))

    dists, denied = list_cloudfront(cf)
    if denied:
        print(denied)
        print("ใช้เว็บผ่าน http://" + dns + ":" + str(PORT) + "/ แทน (ปุ่มกล้องสดต้องใช้ https จะใช้ไม่ได้ ให้ใช้ปุ่มอัปโหลด/ถ่ายรูป)")
        print("ลองเปิด CloudFront ในหน้า Console ด้วย ถ้าขึ้นว่าไม่มีสิทธิ์เหมือนกัน แปลว่า Lab นี้ใช้ CloudFront ไม่ได้ ให้แจ้งอาจารย์")
        sys.exit(1)
    mine = [d for d in dists if d.get("Comment") == CF_COMMENT]
    if mine:
        d = mine[0]
        print("มี CloudFront อยู่แล้ว : " + d["Id"] + " (" + d["Status"] + ")")
        if d["Origins"]["Items"][0]["DomainName"] != dns:
            print("origin ยังชี้ EC2 ตัวเก่า → รัน python3 aws/fix_origin.py")
    else:
        try:
            d = cf.create_distribution(DistributionConfig=config(dns))["Distribution"]
        except Exception as e:   # noqa: BLE001
            print("สร้างด้วยสคริปต์ไม่ได้ : " + type(e).__name__ + " " + str(e)[:200])
            print("ให้สร้างใน Console แทน : CloudFront → Create distribution")
            print("  Origin domain = " + dns + " / Protocol = HTTP only / HTTP port = " + str(PORT))
            print("  Viewer = Redirect HTTP to HTTPS / Allowed methods = GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE")
            print("  Cache policy = CachingDisabled / Origin request policy = AllViewerExceptHostHeader")
            print("  WAF = Do not enable / Description = " + CF_COMMENT)
            sys.exit(1)
        print("สร้างแล้ว CloudFront " + d["Id"])

    url = "https://" + d["DomainName"]
    save_env({"SITE_URL": url, "CF_ID": d["Id"]})
    if args.wait and d["Status"] != "Deployed":
        print("รอ Deployed (ราว 5-10 นาที) ...")
        cf.get_waiter("distribution_deployed").wait(Id=d["Id"], WaiterConfig={"Delay": 30, "MaxAttempts": 40})
    print("\nลิงก์เว็บ : " + url)
    print("ต้องเห็น : CloudFront → Distributions → " + d["Id"] + " สถานะ Deployed (ราว 5-10 นาที) แล้วเปิดลิงก์ด้านบนบนมือถือได้")
    print("ต่อไป → ทดสอบเว็บ แล้ว python3 aws/check.py")


if __name__ == "__main__":
    main()
