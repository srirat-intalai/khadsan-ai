# เอารูปชุดใหม่ที่ตีกรอบเอง (export จาก Roboflow แบบ YOLOv8) มาเตรียมไว้เทรนเพิ่ม
#
# ทำไมต้องมีไฟล์นี้ : เลขคลาสในไฟล์ป้ายของชุดใหม่ มักไม่ตรงกับเลขคลาสของโมเดลเรา
#   เช่น ชุดใหม่มีแค่แอปเปิล Roboflow จะให้ Apple_Bad = 0, Apple_Good = 1 ก็จริง
#   แต่ถ้ามีแค่ส้ม Orange_Bad จะกลายเป็นเลข 0 ซึ่งในโมเดลเรา เลข 0 คือ Apple_Bad
#   ถ้าเอาไปเทรนตรงๆ โมเดลจะเรียนผิด ไฟล์นี้เลยอ่านชื่อคลาสจาก data.yaml แล้วเปลี่ยนเลขให้ตรงกับของเรา
#
# ชื่อคลาสในชุดใหม่ต้องสะกดตรงกับ 10 ชื่อนี้ (ตัวใหญ่ตัวเล็กก็ต้องตรง) คลาสอื่นจะถูกตัดทิ้ง
#   Apple_Bad Apple_Good Banana_Bad Banana_Good Lime_Bad Lime_Good
#   Orange_Bad Orange_Good Pomegranate_Bad Pomegranate_Good
#
# วิธีรัน (ในโฟลเดอร์ train):
#   python add_new_data.py --src โฟลเดอร์ที่แตกzipจากRoboflow --out datasets/kaggle_boxes
#   --out จะเอารูปใหม่ไปต่อท้ายโฟลเดอร์เดิม (ชื่อไฟล์ขึ้นต้นด้วย new_) รูปเดิมในโฟลเดอร์ไม่หาย
#   แล้ว zip โฟลเดอร์ --out เป็น KaggleBoxes.zip ใช้กับ train_round2.ipynb ได้เลย (ดู docs/train-model.md)

import os
import sys
import shutil

SRC_DIR = ""
OUT_DIR = "datasets/kaggle_boxes"

# 10 คลาสของเรา (ลำดับนี้ = เลขคลาสที่โมเดลตอบ ต้องตรงกับ prepare_data.py ห้ามสลับ)
NEW_NAMES = ["Apple_Bad", "Apple_Good", "Banana_Bad", "Banana_Good", "Lime_Bad", "Lime_Good",
             "Orange_Bad", "Orange_Good", "Pomegranate_Bad", "Pomegranate_Good"]

for i in range(len(sys.argv)):
    if sys.argv[i] == "--src":
        SRC_DIR = sys.argv[i + 1]
    if sys.argv[i] == "--out":
        OUT_DIR = sys.argv[i + 1]

if SRC_DIR == "" or not os.path.exists(os.path.join(SRC_DIR, "data.yaml")):
    print("ไม่เจอ data.yaml ใน --src  ให้ชี้ไปที่โฟลเดอร์ที่แตก zip จาก Roboflow (ข้างในมี data.yaml)")
    sys.exit(1)


# อ่านชื่อคลาสจาก data.yaml ได้ 2 แบบ
#   names: ['Apple_Bad', 'Apple_Good']        (บรรทัดเดียว)
#   names:                                    (หลายบรรทัด)
#     - Apple_Bad        หรือ     0: Apple_Bad
def read_names(yaml_file):
    names = []
    reading = False
    for line in open(yaml_file, encoding="utf-8"):
        if line.startswith("names:"):
            text = line.split(":", 1)[1].strip()
            if text.startswith("["):
                for n in text.strip("[]").split(","):
                    names.append(n.strip().strip("'\""))
                return names
            reading = True
            continue
        if reading:
            text = line.strip()
            if text.startswith("- "):
                names.append(text[2:].strip().strip("'\""))
            elif ":" in text and text.split(":")[0].strip().isdigit():
                names.append(text.split(":", 1)[1].strip().strip("'\""))
            else:
                break
    return names


old_names = read_names(os.path.join(SRC_DIR, "data.yaml"))
print("คลาสในชุดใหม่:", old_names)
for n in old_names:
    if n not in NEW_NAMES:
        print("  !!", n, "ไม่ใช่ 1 ใน 10 คลาสของเรา กรอบของคลาสนี้จะถูกตัดทิ้ง (ถ้าสะกดผิด ให้แก้ชื่อใน Roboflow แล้ว export ใหม่)")

os.makedirs(os.path.join(OUT_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(OUT_DIR, "labels"), exist_ok=True)

saved = 0
no_box = 0
dropped_boxes = 0
count = [0] * len(NEW_NAMES)

# Roboflow แบ่งไว้เป็น train / valid / test เราเอามาเป็นรูปเทรนทั้งหมด
# (val กับ test ของเราใช้ชุดเดิม คะแนนจะได้เทียบกับรอบก่อนได้)
for part in ["train", "valid", "test"]:
    img_folder = os.path.join(SRC_DIR, part, "images")
    lab_folder = os.path.join(SRC_DIR, part, "labels")
    if not os.path.isdir(img_folder):
        continue
    for f in sorted(os.listdir(img_folder)):
        if not f.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        label_file = os.path.join(lab_folder, os.path.splitext(f)[0] + ".txt")
        lines = []
        if os.path.exists(label_file):
            for line in open(label_file, encoding="utf-8"):
                p = line.split()
                if len(p) != 5:
                    continue
                name = old_names[int(p[0])]
                if name in NEW_NAMES:
                    k = NEW_NAMES.index(name)
                    lines.append(str(k) + " " + " ".join(p[1:]))
                    count[k] = count[k] + 1
                else:
                    dropped_boxes = dropped_boxes + 1

        # รูปที่ไม่มีกรอบของเราเลย ไม่เอา (ถ้าตั้งใจใส่รูปพื้นหลังไม่มีผลไม้ ใช้ prepare_data.py --make-boxes แทน)
        if len(lines) == 0:
            no_box = no_box + 1
            continue

        new_name = "new_" + part + "_" + f
        shutil.copy(os.path.join(img_folder, f), os.path.join(OUT_DIR, "images", new_name))
        with open(os.path.join(OUT_DIR, "labels", os.path.splitext(new_name)[0] + ".txt"), "w", encoding="utf-8") as out:
            out.write("\n".join(lines) + "\n")
        saved = saved + 1

print("เพิ่มรูปใหม่", saved, "รูป ไว้ที่", os.path.abspath(OUT_DIR))
print("ข้ามรูปที่ไม่มีกรอบ", no_box, "รูป | ตัดกรอบคลาสอื่นทิ้ง", dropped_boxes, "กรอบ")
print("กรอบต่อคลาส", dict(zip(NEW_NAMES, count)))
print("ตอนนี้ในโฟลเดอร์มีรูปรวม", len(os.listdir(os.path.join(OUT_DIR, "images"))), "รูป",
      "/ ไฟล์ป้าย", len(os.listdir(os.path.join(OUT_DIR, "labels"))), "ไฟล์ (2 ตัวเลขนี้ต้องเท่ากัน)")
