# เอารูปชุดใหม่ที่ตีกรอบแล้ว (export จาก Roboflow แบบ YOLOv8) มาเตรียมไว้เทรนเพิ่ม หรือทำเป็นข้อสอบใหม่
#
# ทำไมต้องมีไฟล์นี้ : เลขคลาสในไฟล์ป้ายของชุดใหม่ มักไม่ตรงกับเลขคลาสของโมเดลเรา
#   เช่น ชุดใหม่มีแค่ส้ม Orange_Bad จะกลายเป็นเลข 0 ซึ่งในโมเดลเรา เลข 0 คือ Apple_Bad
#   ถ้าเอาไปเทรนตรงๆ โมเดลจะเรียนผิด ไฟล์นี้เลยอ่านชื่อคลาสจาก data.yaml แล้วเปลี่ยนเลขให้ตรงกับของเรา
#
# ชื่อคลาสที่ใช้ได้ (ตัวใหญ่ตัวเล็กต้องตรง) คลาสอื่นจะถูกตัดทิ้ง
#   Apple_Bad Apple_Good Banana_Bad Banana_Good Lime_Bad Lime_Good
#   Orange_Bad Orange_Good Pomegranate_Bad Pomegranate_Good
#
# วิธีรัน (ในโฟลเดอร์ train):
#   python add_new_data.py --src โฟลเดอร์ที่แตกzipจากRoboflow --out datasets/kaggle_boxes
#   --out จะเอารูปใหม่ไปต่อท้ายโฟลเดอร์เดิม รูปเดิมในโฟลเดอร์ไม่หาย
#   แล้ว zip โฟลเดอร์ --out เป็น KaggleBoxes.zip ใช้กับ train_round2.ipynb / train_round3.ipynb ได้เลย (ดู docs/train-model.md)
#
# ตัวเลือกเพิ่ม (รอบ 3)
#   --rename "rotten_orange=Orange_Bad,fresh_orange=Orange_Good"
#       ชุดของคนอื่นตั้งชื่อคลาสไม่เหมือนเรา บอกตรงนี้ว่าชื่อไหนคือคลาสไหนของเรา ไม่ต้องไปแก้ data.yaml เอง
#   --avoid "datasets/data_5fruits/val/images,datasets/external_test"
#       ข้ามรูปที่หน้าตาคล้ายรูปในโฟลเดอร์พวกนี้ (กันข้อสอบรั่วเข้าชุดเทรน) ใส่ได้หลายโฟลเดอร์ คั่นด้วย ,
#   --per-class 150
#       เอาคลาสละไม่เกินกี่รูป (สุ่มแบบล็อก seed ได้รูปเดิมทุกครั้ง) ใช้ตอนทำข้อสอบจากชุดที่ใหญ่มาก
#   --prefix lq_
#       ขึ้นต้นชื่อไฟล์ จะได้รู้ว่ารูปมาจากชุดไหน (ไม่ใส่ = new_)
#
# สิ่งที่ไฟล์นี้ทำให้เอง
#   - ป้ายแบบเส้นรอบรูป (polygon) แปลงเป็นกรอบสี่เหลี่ยม
#   - Roboflow ชอบทำรูปเดิมเป็นหลายเวอร์ชัน (หมุน กลับด้าน) เก็บไว้แค่รูปเดียวต่อรูปต้นฉบับ
#   - รูปในชุดเดียวกันที่หน้าตาเกือบเหมือนกัน เก็บไว้รูปเดียว

import os
import sys
import random
import shutil
from PIL import Image

SRC_DIR = ""
OUT_DIR = "datasets/kaggle_boxes"
RENAME = {}           # ชื่อคลาสของชุดใหม่ -> ชื่อคลาสของเรา
AVOID_DIRS = []       # โฟลเดอร์รูปที่ห้ามซ้ำ
PER_CLASS = 0         # 0 = ไม่จำกัด
PREFIX = "new_"
SEED = 42
SAME_PICTURE = 6      # ลายนิ้วมือรูปต่างกันไม่เกิน 6 จุด (จาก 64) = รูปเกือบเหมือนกัน (ค่าเดียวกับ prepare_data.py)

# 10 คลาสของเรา (ลำดับนี้ = เลขคลาสที่โมเดลตอบ ต้องตรงกับ prepare_data.py ห้ามสลับ)
NEW_NAMES = ["Apple_Bad", "Apple_Good", "Banana_Bad", "Banana_Good", "Lime_Bad", "Lime_Good",
             "Orange_Bad", "Orange_Good", "Pomegranate_Bad", "Pomegranate_Good"]

for i in range(len(sys.argv)):
    if sys.argv[i] == "--src":
        SRC_DIR = sys.argv[i + 1]
    if sys.argv[i] == "--out":
        OUT_DIR = sys.argv[i + 1]
    if sys.argv[i] == "--rename":
        for pair in sys.argv[i + 1].split(","):
            old, new = pair.split("=")
            RENAME[old.strip()] = new.strip()
    if sys.argv[i] == "--avoid":
        for d in sys.argv[i + 1].split(","):
            AVOID_DIRS.append(d.strip())
    if sys.argv[i] == "--per-class":
        PER_CLASS = int(sys.argv[i + 1])
    if sys.argv[i] == "--prefix":
        PREFIX = sys.argv[i + 1]

if SRC_DIR == "" or not os.path.exists(os.path.join(SRC_DIR, "data.yaml")):
    print("ไม่เจอ data.yaml ใน --src  ให้ชี้ไปที่โฟลเดอร์ที่แตก zip จาก Roboflow (ข้างในมี data.yaml)")
    sys.exit(1)

for n in RENAME.values():
    if n not in NEW_NAMES:
        print("--rename ใส่", n, "ซึ่งไม่ใช่ 1 ใน 10 คลาสของเรา (สะกดผิดหรือเปล่า)")
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


# ลายนิ้วมือรูป (แบบเดียวกับ prepare_data.py) : ย่อเหลือ 9x8 ขาวดำ ได้เลข 0/1 มา 64 ตัว
def picture_print(img):
    small = img.convert("L").resize((9, 8))
    px = list(small.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            if px[row * 9 + col] > px[row * 9 + col + 1]:
                bits = bits * 2 + 1
            else:
                bits = bits * 2
    return bits


def count_diff(a, b):
    return bin(a ^ b).count("1")


def is_same_as(p, prints):
    for q in prints:
        if count_diff(p, q) <= SAME_PICTURE:
            return True
    return False


# ป้าย 1 บรรทัด -> กรอบ "x y w h" (ถ้าเป็นเส้นรอบรูป ใช้จุดซ้ายสุด ขวาสุด บนสุด ล่างสุด มาทำกรอบ)
def to_box(numbers):
    if len(numbers) == 4:
        return numbers
    xs = numbers[0::2]
    ys = numbers[1::2]
    x1 = min(xs)
    x2 = max(xs)
    y1 = min(ys)
    y2 = max(ys)
    return [(x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1]


old_names = read_names(os.path.join(SRC_DIR, "data.yaml"))
print("คลาสในชุดใหม่:", old_names)
for n in old_names:
    if n not in NEW_NAMES and n not in RENAME:
        print("  !!", n, "ไม่ใช่ 1 ใน 10 คลาสของเรา และไม่ได้ใส่ใน --rename กรอบของคลาสนี้จะถูกตัดทิ้ง")

# ลายนิ้วมือของรูปที่ห้ามซ้ำ (ไล่ทุกโฟลเดอร์ย่อย)
avoid_prints = []
for d in AVOID_DIRS:
    for root, dirs, files in os.walk(d):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                with Image.open(os.path.join(root, f)) as im:
                    avoid_prints.append(picture_print(im))
if len(AVOID_DIRS) > 0:
    print("ลายนิ้วมือรูปที่ห้ามซ้ำ", len(avoid_prints), "รูป จาก", AVOID_DIRS)

# อ่านรูปทั้งหมดก่อน แล้วค่อยสุ่มลำดับ (ล็อก seed) จะได้เลือกรูปเหมือนเดิมทุกครั้ง
items = []
for part in ["train", "valid", "test"]:
    img_folder = os.path.join(SRC_DIR, part, "images")
    if os.path.isdir(img_folder):
        for f in sorted(os.listdir(img_folder)):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                items.append((part, f))
random.Random(SEED).shuffle(items)

os.makedirs(os.path.join(OUT_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(OUT_DIR, "labels"), exist_ok=True)

saved = 0
no_box = 0
dropped_boxes = 0
copy_version = 0
same_inside = 0
same_avoid = 0
full = 0
count = [0] * len(NEW_NAMES)        # กรอบต่อคลาส
image_count = [0] * len(NEW_NAMES)  # รูปต่อคลาส (ใช้กับ --per-class)
seen_source = []                    # ชื่อรูปต้นฉบับที่เอาไปแล้ว
kept_prints = []

# รันซ้ำด้วย --prefix เดิม ให้เลขต่อจากไฟล์ที่มีอยู่ ไฟล์เก่าจะได้ไม่โดนทับ
start = 0
for f in os.listdir(os.path.join(OUT_DIR, "images")):
    if f.startswith(PREFIX):
        start = start + 1

# Roboflow แบ่งไว้เป็น train / valid / test เราไม่ใช้การแบ่งของเขา เอามารวมกันหมด
for part, f in items:
    img_path = os.path.join(SRC_DIR, part, "images", f)
    label_file = os.path.join(SRC_DIR, part, "labels", os.path.splitext(f)[0] + ".txt")

    # รูปที่ Roboflow ทำเพิ่มจากรูปเดิม ชื่อจะเป็น "ชื่อเดิม_jpg.rf.xxxx.jpg" เก็บแค่รูปแรกของแต่ละชื่อเดิม
    source = f.split(".rf.")[0]
    if source in seen_source:
        copy_version = copy_version + 1
        continue

    lines = []
    classes = []
    if os.path.exists(label_file):
        for line in open(label_file, encoding="utf-8"):
            p = line.split()
            if len(p) < 5:
                continue
            name = old_names[int(p[0])]
            if name in RENAME:
                name = RENAME[name]
            if name not in NEW_NAMES:
                dropped_boxes = dropped_boxes + 1
                continue
            k = NEW_NAMES.index(name)
            box = to_box([float(x) for x in p[1:]])
            lines.append(str(k) + " " + " ".join(str(round(v, 6)) for v in box))
            if k not in classes:
                classes.append(k)

    # รูปที่ไม่มีกรอบของเราเลย ไม่เอา
    if len(lines) == 0:
        no_box = no_box + 1
        continue

    # --per-class : ทุกคลาสในรูปนี้ครบจำนวนแล้ว ไม่เอา
    if PER_CLASS > 0:
        need = False
        for k in classes:
            if image_count[k] < PER_CLASS:
                need = True
        if not need:
            full = full + 1
            continue

    with Image.open(img_path) as im:
        p = picture_print(im)
    if is_same_as(p, avoid_prints):
        same_avoid = same_avoid + 1
        continue
    if is_same_as(p, kept_prints):
        same_inside = same_inside + 1
        continue

    seen_source.append(source)
    kept_prints.append(p)
    new_name = PREFIX + str(start + saved + 1).zfill(4) + os.path.splitext(f)[1].lower()
    shutil.copy(img_path, os.path.join(OUT_DIR, "images", new_name))
    with open(os.path.join(OUT_DIR, "labels", os.path.splitext(new_name)[0] + ".txt"), "w", encoding="utf-8") as out:
        out.write("\n".join(lines) + "\n")
    for line in lines:
        count[int(line.split()[0])] += 1
    for k in classes:
        image_count[k] += 1
    saved = saved + 1

print("เพิ่มรูปใหม่", saved, "รูป ไว้ที่", os.path.abspath(OUT_DIR))
print("ข้าม: รูปที่ Roboflow ทำซ้ำ", copy_version, "| ซ้ำกันเองในชุด", same_inside,
      "| คล้ายรูปที่ห้ามซ้ำ", same_avoid, "| ไม่มีกรอบ", no_box, "| ครบจำนวนแล้ว", full)
print("ตัดกรอบคลาสอื่นทิ้ง", dropped_boxes, "กรอบ")
print("รูปต่อคลาส", {NEW_NAMES[k]: image_count[k] for k in range(len(NEW_NAMES)) if image_count[k] > 0})
print("กรอบต่อคลาส", {NEW_NAMES[k]: count[k] for k in range(len(NEW_NAMES)) if count[k] > 0})
print("ตอนนี้ในโฟลเดอร์มีรูปรวม", len(os.listdir(os.path.join(OUT_DIR, "images"))), "รูป",
      "/ ไฟล์ป้าย", len(os.listdir(os.path.join(OUT_DIR, "labels"))), "ไฟล์ (2 ตัวเลขนี้ต้องเท่ากัน)")
