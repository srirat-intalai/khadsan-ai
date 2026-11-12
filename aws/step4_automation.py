# ขั้น 4 ของ workshop (รันใน AWS CloudShell) : python3 aws/step4_automation.py
#   - Lambda KhadsanDailySummary (Python 3.12, role LabRole) โค้ดจาก aws/lambda_summary.py
#     ตั้ง Environment variables S3_BUCKET / SNS_TOPIC_ARN ให้เอง (ไม่ต้องพิมพ์ ARN เอง)
#   - EventBridge rule khadsan-daily-1800 = cron(0 11 * * ? *) = ทุกวัน 18:00 เวลาไทย → Lambda
#     ให้สิทธิ์ EventBridge เรียก Lambda ที่ตัว Lambda เอง (Learner Lab สร้าง IAM role ใหม่ไม่ได้)
#   - ทดสอบเรียก Lambda 1 ครั้ง → ได้อีเมลสรุปทันที
# รันซ้ำได้ ถ้ามีอยู่แล้วจะอัปเดตโค้ดและค่าให้ตรง

import io
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *   # noqa: F401,F403

CODE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lambda_summary.py")


def code_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(CODE, "lambda_function.py")
    return buf.getvalue()


def ensure_lambda(lam, role_arn, env_vars):
    cfg = {"Role": role_arn, "Handler": "lambda_function.lambda_handler", "Runtime": "python3.12",
           "Timeout": 60, "MemorySize": 128, "Environment": {"Variables": env_vars},
           "Description": "KhadSan AI daily summary (S3 logs -> SNS)"}
    try:
        lam.get_function(FunctionName=LAMBDA)
        lam.update_function_code(FunctionName=LAMBDA, ZipFile=code_zip())
        lam.get_waiter("function_updated_v2").wait(FunctionName=LAMBDA)
        lam.update_function_configuration(FunctionName=LAMBDA, **cfg)
        print("  อัปเดตแล้ว Lambda " + LAMBDA)
    except lam.exceptions.ResourceNotFoundException:
        lam.create_function(FunctionName=LAMBDA, Code={"ZipFile": code_zip()}, **cfg)
        print("  สร้างแล้ว  Lambda " + LAMBDA)
    lam.get_waiter("function_active_v2").wait(FunctionName=LAMBDA)
    lam.get_waiter("function_updated_v2").wait(FunctionName=LAMBDA)
    return lam.get_function(FunctionName=LAMBDA)["Configuration"]["FunctionArn"]


def ensure_rule(events, lam, fn_arn):
    rule_arn = events.put_rule(Name=RULE, ScheduleExpression=CRON, State="ENABLED",
                               Description="KhadSan AI daily summary 18:00 Thailand time")["RuleArn"]
    print("  rule " + RULE + " " + CRON + " (ENABLED)")
    try:
        lam.add_permission(FunctionName=LAMBDA, StatementId=RULE, Action="lambda:InvokeFunction",
                           Principal="events.amazonaws.com", SourceArn=rule_arn)
        print("  ให้สิทธิ์ EventBridge เรียก Lambda แล้ว")
    except lam.exceptions.ResourceConflictException:
        print("  สิทธิ์ EventBridge → Lambda มีอยู่แล้ว")
    r = events.put_targets(Rule=RULE, Targets=[{"Id": "1", "Arn": fn_arn}])
    if r["FailedEntryCount"]:
        sys.exit("ตั้ง target ไม่สำเร็จ : " + json.dumps(r["FailedEntries"]))
    print("  target = Lambda " + LAMBDA)


def main():
    s = session()
    env = load_env()
    acct = account_id(s)
    bucket = pick_bucket(s.client("s3"), env)
    topic = env.get("SNS_TOPIC_ARN") or find_topic_arn(s.client("sns"))
    if not bucket or not topic:
        sys.exit("ยังไม่มี S3 bucket หรือ SNS topic ให้รัน python3 aws/step2_storage_alerts.py ก่อน")
    lam, events = s.client("lambda"), s.client("events")
    role_arn = "arn:aws:iam::" + acct + ":role/" + LAMBDA_ROLE

    print("[1/3] Lambda")
    fn_arn = ensure_lambda(lam, role_arn, {"S3_BUCKET": bucket, "SNS_TOPIC_ARN": topic})
    print("\n[2/3] EventBridge")
    ensure_rule(events, lam, fn_arn)

    print("\n[3/3] ทดสอบเรียก Lambda")
    r = lam.invoke(FunctionName=LAMBDA, Payload=b"{}")
    body = r["Payload"].read().decode("utf-8")
    if r.get("FunctionError"):
        sys.exit("  Lambda error : " + body)
    print("  ผล : " + body)

    print("\nต้องเห็น : statusCode 200 และได้อีเมล 'KhadSan AI Daily Summary - <วันนี้>' (ยังไม่มีการสแกน ตัวเลขเป็น 0 ได้)")
    print("ดูผลใน Console : Lambda → " + LAMBDA + " → Configuration → Triggers = EventBridge  /  EventBridge → Rules → " + RULE)
    print("ดู log ใน CloudWatch : CloudWatch → Log groups → /aws/lambda/" + LAMBDA + " → stream ล่าสุด (บรรทัด START / END / REPORT)")
    print("ต่อไป → python3 aws/step5_cloudfront.py (เมื่อเว็บบน EC2 ตอบ 200 แล้ว)")


if __name__ == "__main__":
    main()
