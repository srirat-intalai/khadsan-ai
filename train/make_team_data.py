# รอบ 4 : แบ่งชุดรูปที่ทีมรวบรวมเพิ่ม เป็นรูปเทรนกับข้อสอบ
# มะนาว/ทับทิม (จุดอ่อนรอบ 3) ครึ่งหนึ่งไปเทรน อีกครึ่งเป็นข้อสอบ ผลไม้อื่นเป็นข้อสอบทั้งหมด
# รูปไม่มีกรอบ เลยให้โมเดล 11 ร่างกรอบ (คลาสใช้ชื่อโฟลเดอร์) แล้วคนเปิดดูทีละรูป
# วิธีรัน (ในโฟลเดอร์ train)
#   1) python make_team_data.py --draft  -> ข้อสอบ datasets/team_collected_test + กรอบร่างใน datasets/team_train_draft
#   2) ดูรูปใน team_train_draft/preview ใส่ชื่อรูปที่กรอบผิด/ไม่ครบลง reject.txt
#   3) python make_team_data.py --build  -> datasets/kaggle_boxes_v4 = kaggle_boxes_v3 + รูปที่ผ่าน (ขึ้นต้น tc_)

import os
import sys
import random
import shutil
from PIL import Image, ImageDraw

TEAM_DIR = "datasets/team_collected_web"
TEST_DIR = "datasets/team_collected_test"
DRAFT_DIR = "datasets/team_train_draft"
OLD_EXTRA = "datasets/kaggle_boxes_v3"
NEW_EXTRA = "datasets/kaggle_boxes_v4"
MODEL = "../web/models/best_detect.pt"   # โมเดล 11

TRAIN_CLASSES = ["Lime_Bad", "Lime_Good", "Pomegranate_Bad", "Pomegranate_Good"]   # คลาสที่แบ่งไปเทรน
TRAIN_PART = 0.5      # แบ่งไปเทรนครึ่งหนึ่ง
DRAFT_CONF = 0.10     # ความมั่นใจตอนร่างกรอบ (ต่ำไว้ ไม่พลาดลูกที่โมเดลไม่มั่นใจ)
SEED = 42

# 10 คลาสของเรา (ลำดับ = เลขคลาส ต้องตรงกับ prepare_data.py)
NAMES = ["Apple_Bad", "Apple_Good", "Banana_Bad", "Banana_Good", "Lime_Bad", "Lime_Good",
         "Orange_Bad", "Orange_Good", "Pomegranate_Bad", "Pomegranate_Good"]


def list_images(folder):
    files = []
    for f in sorted(os.listdir(folder)):
        if f.lower().endswith((".jpg", ".jpeg", ".png")):
            files.append(f)
    return files


def draft():
    from ultralytics import YOLO
    model = YOLO(MODEL)
    for d in [TEST_DIR, DRAFT_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
    for sub in ["images", "labels", "preview"]:
        os.makedirs(os.path.join(DRAFT_DIR, sub))

    no_box = []
    for name in NAMES:
        folder = os.path.join(TEAM_DIR, name)
        if not os.path.isdir(folder):
            continue
        files = list_images(folder)
        random.Random(SEED).shuffle(files)       # สุ่มแบบล็อก seed
        n_train = 0
        if name in TRAIN_CLASSES:
            n_train = int(len(files) * TRAIN_PART)
        train_files = files[:n_train]
        test_files = files[n_train:]

        # ส่วนข้อสอบ : ก๊อปไปตามโฟลเดอร์คลาส
        os.makedirs(os.path.join(TEST_DIR, name))
        for f in test_files:
            shutil.copy(os.path.join(folder, f), os.path.join(TEST_DIR, name, f))

        # ส่วนเทรน : โมเดลร่างกรอบ (agnostic_nms = กรอบซ้อนคนละคลาสเหลืออันเดียว)
        k = NAMES.index(name)
        for f in train_files:
            img_path = os.path.join(folder, f)
            r = model.predict(img_path, imgsz=640, conf=DRAFT_CONF, agnostic_nms=True, verbose=False)[0]
            if len(r.boxes) == 0:
                no_box.append(f)
                continue
            lines = []
            for box in r.boxes.xywhn.tolist():
                lines.append(str(k) + " " + " ".join(str(round(v, 6)) for v in box))
            new_name = "tc_" + f
            shutil.copy(img_path, os.path.join(DRAFT_DIR, "images", new_name))
            with open(os.path.join(DRAFT_DIR, "labels", os.path.splitext(new_name)[0] + ".txt"), "w") as out:
                out.write("\n".join(lines) + "\n")
            # วาดกรอบไว้ให้คนดู
            im = Image.open(img_path).convert("RGB")
            pen = ImageDraw.Draw(im)
            for x1, y1, x2, y2 in r.boxes.xyxy.tolist():
                pen.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=4)
            im.save(os.path.join(DRAFT_DIR, "preview", new_name), quality=85)
        print(f"{name:17} เทรน {len(train_files):3} รูป | ข้อสอบ {len(test_files):3} รูป")

    open(os.path.join(DRAFT_DIR, "reject.txt"), "w").close()
    print("โมเดลหากรอบไม่เจอ (ไม่เอาไปเทรน)", len(no_box), "รูป")
    print("ร่างกรอบได้", len(os.listdir(os.path.join(DRAFT_DIR, "images"))), "รูป ไปเปิดดูที่", os.path.join(DRAFT_DIR, "preview"))


def build():
    reject = []
    reject_file = os.path.join(DRAFT_DIR, "reject.txt")
    if os.path.exists(reject_file):
        for line in open(reject_file, encoding="utf-8"):
            if line.strip() != "" and not line.startswith("#"):
                reject.append(line.split()[0])
    if os.path.exists(NEW_EXTRA):
        shutil.rmtree(NEW_EXTRA)
    shutil.copytree(OLD_EXTRA, NEW_EXTRA)        # รูปเทรนเพิ่มของรอบ 3
    added = {}
    for f in list_images(os.path.join(DRAFT_DIR, "images")):
        if f in reject:
            continue
        label = os.path.splitext(f)[0] + ".txt"
        shutil.copy(os.path.join(DRAFT_DIR, "images", f), os.path.join(NEW_EXTRA, "images", f))
        shutil.copy(os.path.join(DRAFT_DIR, "labels", label), os.path.join(NEW_EXTRA, "labels", label))
        k = int(open(os.path.join(DRAFT_DIR, "labels", label)).readline().split()[0])
        added[NAMES[k]] = added.get(NAMES[k], 0) + 1
    print("ไม่ผ่าน (reject.txt)", len(reject), "รูป")
    print("เพิ่มรูปทีมเข้าชุดเทรน", sum(added.values()), "รูป", added)
    print("kaggle_boxes_v4 มีรูป", len(os.listdir(os.path.join(NEW_EXTRA, "images"))), "รูป / ไฟล์ป้าย",
          len(os.listdir(os.path.join(NEW_EXTRA, "labels"))), "ไฟล์ (2 ตัวเลขนี้ต้องเท่ากัน)")


if "--draft" in sys.argv:
    draft()
elif "--build" in sys.argv:
    build()
else:
    print("ใส่ --draft (ร่างกรอบ) หรือ --build (รวมชุดเทรน)")
