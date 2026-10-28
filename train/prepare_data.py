# เตรียมข้อมูลก่อนเทรน YOLOv8 (ไฟล์เดียวจบ ทำ 2 ส่วน)
#
# ส่วนที่ 1 : ชุดเทรน จาก "Fruits Quality" (Roboflow alex-day-qzfwa/fruits-quality-qtdtf v1, CC BY 4.0)
#   - เก็บแค่ผลไม้ 5 ชนิด x สด/เน่า = 10 คลาส (ตัดฝรั่ง กับคลาสแปลกๆ ทิ้ง)
#   - รูปที่หน้าตาเกือบเหมือนกัน (ถ่ายลูกเดิมหลายช็อต) จับไว้กลุ่มเดียวกัน
#     ไม่ให้ไปโผล่ทั้งใน train และ test (ไม่งั้นคะแนน test จะดูดีเกินจริง = data leakage)
#   - แบ่งใหม่ 70 / 15 / 15 แล้วเขียน data.yaml ให้ YOLO
#
# ส่วนที่ 2 : ชุดทดสอบภายนอก จาก Kaggle "Fruit Diseases" (มีแค่ แอปเปิล กล้วย ส้ม ไม่มีกรอบ)
#   - เอาไว้สอบโมเดลกับรูปจากแหล่งอื่นที่โมเดลไม่เคยเห็น
#   - คลาสละไม่เกิน 100 รูป ข้ามรูปซ้ำ ย่อรูป เปลี่ยนชื่อคลาสให้ตรงกับโมเดล
#   - ถ้าไม่มีโฟลเดอร์ Kaggle (เช่นตอนรันบน Colab) ส่วนนี้ข้ามไปเอง
#
# วิธีรัน (ในโฟลเดอร์ train):  python prepare_data.py
# เปลี่ยนที่อยู่ได้:  python prepare_data.py --src โฟลเดอร์FruitsQuality --out โฟลเดอร์ผลลัพธ์

import os
import sys
import csv
import random
import shutil
from PIL import Image


# ===== ตั้งค่า =====
SRC_DIR = "datasets/fruits_quality"               # ชุดเทรน (Roboflow)
OUT_DIR = "datasets/data_5fruits"                 # ที่เก็บชุดเทรนที่แบ่งแล้ว
KAGGLE_DIR = "datasets/fruit_diseases_kaggle"     # ชุดทดสอบภายนอก (Kaggle) ไม่มีก็ได้
EXTERNAL_DIR = "datasets/external_test"           # ที่เก็บชุดทดสอบภายนอก

# ชื่อคลาสในชุดเดิมของ Roboflow (เรียงตาม data.yaml ของเขา ห้ามสลับ)
OLD_NAMES = ["Apple_Bad", "Apple_Good", "Banana_Bad", "Banana_Good", "Good_Apple-Bad_Apple",
             "Guava_Bad", "Guava_Good", "Lime_Bad", "Lime_Good", "Orange_Bad", "Orange_Good",
             "Pomegranate_Bad", "Pomegranate_Good"]

# 10 คลาสที่เราใช้ (ลำดับนี้ = เลขคลาสที่โมเดลจะตอบ)
NEW_NAMES = ["Apple_Bad", "Apple_Good", "Banana_Bad", "Banana_Good", "Lime_Bad", "Lime_Good",
             "Orange_Bad", "Orange_Good", "Pomegranate_Bad", "Pomegranate_Good"]

# ชื่อโฟลเดอร์ของ Kaggle -> ชื่อคลาสของเรา
KAGGLE_NAMES = {
    "Apple__Healthy": "Apple_Good", "Apple__Rotten": "Apple_Bad",
    "Banana__Healthy": "Banana_Good", "Banana__Rotten": "Banana_Bad",
    "Orange__Healthy": "Orange_Good", "Orange__Rotten": "Orange_Bad",
}

TRAIN_PART = 0.70
VAL_PART = 0.15         # ที่เหลือ 15% เป็น test
SEED = 42
SAME_PICTURE = 6        # ลายนิ้วมือรูปต่างกันไม่เกิน 6 จุด (จาก 64) = รูปเกือบเหมือนกัน
EXTERNAL_PER_CLASS = 100
EXTERNAL_MAX_SIDE = 640

for i in range(len(sys.argv)):
    if sys.argv[i] == "--src":
        SRC_DIR = sys.argv[i + 1]
    if sys.argv[i] == "--out":
        OUT_DIR = sys.argv[i + 1]


# ===== ใช้ร่วมกันทั้ง 2 ส่วน =====

# แปลงรูปเป็น RGB  (png พื้นโปร่งใส ถ้าแปลงตรงๆ พื้นจะดำ เลยวางบนพื้นขาวก่อน แบบเดียวกับเว็บ)
def to_rgb(img):
    if "A" in img.mode or "transparency" in img.info:
        img = img.convert("RGBA")
        white = Image.new("RGB", img.size, "white")
        white.paste(img, mask=img)
        return white
    return img.convert("RGB")


# ลายนิ้วมือรูป : ย่อเหลือ 9x8 ขาวดำ แล้วดูว่าแต่ละจุดสว่างกว่าจุดข้างขวาไหม ได้เลข 0/1 มา 64 ตัว
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


# ลายนิ้วมือ 2 รูป ต่างกันกี่จุด (น้อย = หน้าตาคล้ายกัน)
def count_diff(a, b):
    return bin(a ^ b).count("1")


# =====================================================================
# ส่วนที่ 1 : ชุดเทรน
# =====================================================================

# อ่านรูปทั้งหมด (รวม train/valid/test เดิม) แล้วเปลี่ยนเลขคลาสเป็นแบบใหม่
def read_all_images():
    items = []
    dropped_boxes = 0
    dropped_images = 0
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
                    old_name = OLD_NAMES[int(p[0])]
                    if old_name in NEW_NAMES:
                        new_id = NEW_NAMES.index(old_name)
                        lines.append(str(new_id) + " " + " ".join(p[1:]))
                    else:
                        dropped_boxes = dropped_boxes + 1

            # รูปที่ไม่เหลือกรอบของ 5 ชนิดเลย (เช่น มีแต่ฝรั่ง) ไม่เอา
            if len(lines) == 0:
                dropped_images = dropped_images + 1
                continue
            items.append({"image": os.path.join(img_folder, f), "name": f, "lines": lines})

    print("ตัดกรอบที่ไม่ใช่ 5 ชนิดทิ้ง", dropped_boxes, "กรอบ | ตัดรูปที่ไม่เหลือกรอบ", dropped_images, "รูป")
    return items


# จับกลุ่มรูปที่คล้ายกัน
# ไล่ทีละรูป ถ้าคล้ายกับรูปไหนในกลุ่มที่มีอยู่แล้ว ก็ใส่กลุ่มนั้น ถ้าไม่คล้ายใครเลย ก็เปิดกลุ่มใหม่
def make_groups(items):
    groups = []      # แต่ละกลุ่ม = list ของรูป
    prints = []      # ลายนิ้วมือของรูปในแต่ละกลุ่ม (ลำดับเดียวกับ groups)
    for it in items:
        with Image.open(it["image"]) as im:
            p = picture_print(im)

        found = -1
        for g in range(len(groups)):
            for q in prints[g]:
                if count_diff(p, q) <= SAME_PICTURE:
                    found = g
                    break
            if found != -1:
                break

        if found == -1:
            groups.append([it])
            prints.append([p])
        else:
            groups[found].append(it)
            prints[found].append(p)
    return groups


# แบ่งกลุ่มเป็น train / val / test (ทั้งกลุ่มไปอยู่ชุดเดียวกัน)
def split_groups(groups):
    rng = random.Random(SEED)
    rng.shuffle(groups)
    total = 0
    for g in groups:
        total = total + len(g)

    train = []
    val = []
    test = []
    for g in groups:
        if len(train) < total * TRAIN_PART:
            train.extend(g)
        elif len(val) < total * VAL_PART:
            val.extend(g)
        else:
            test.extend(g)
    return {"train": train, "val": val, "test": test}


# เขียนไฟล์ออกไปเป็นรูปแบบที่ YOLO ต้องการ + ตารางจำนวน ไว้ใส่รายงาน
def write_dataset(splits):
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    rows = []
    for part in ["train", "val", "test"]:
        os.makedirs(os.path.join(OUT_DIR, part, "images"))
        os.makedirs(os.path.join(OUT_DIR, part, "labels"))
        count = [0] * len(NEW_NAMES)
        for it in splits[part]:
            shutil.copy(it["image"], os.path.join(OUT_DIR, part, "images", it["name"]))
            label_path = os.path.join(OUT_DIR, part, "labels", os.path.splitext(it["name"])[0] + ".txt")
            with open(label_path, "w", encoding="utf-8") as f:
                f.write("\n".join(it["lines"]) + "\n")
            for line in it["lines"]:
                k = int(line.split()[0])
                count[k] = count[k] + 1
        rows.append([part, len(splits[part])] + count)
        print(part, "รูป", len(splits[part]), "| กรอบต่อคลาส", dict(zip(NEW_NAMES, count)))

    # data.yaml บอก YOLO ว่ารูปอยู่ไหน และมีคลาสอะไร
    names_text = ""
    for n in NEW_NAMES:
        if names_text != "":
            names_text = names_text + ", "
        names_text = names_text + "'" + n + "'"
    with open(os.path.join(OUT_DIR, "data.yaml"), "w", encoding="utf-8") as f:
        f.write("path: " + os.path.abspath(OUT_DIR) + "\n")
        f.write("train: train/images\nval: val/images\ntest: test/images\n")
        f.write("nc: " + str(len(NEW_NAMES)) + "\n")
        f.write("names: [" + names_text + "]\n")

    with open(os.path.join(OUT_DIR, "dataset_counts.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["split", "images"] + NEW_NAMES)
        for row in rows:
            writer.writerow(row)


# =====================================================================
# ส่วนที่ 2 : ชุดทดสอบภายนอก (Kaggle)
# =====================================================================
def make_external_test():
    rng = random.Random(SEED)
    for old_name in sorted(KAGGLE_NAMES):
        new_name = KAGGLE_NAMES[old_name]
        src_folder = os.path.join(KAGGLE_DIR, old_name)
        out_folder = os.path.join(EXTERNAL_DIR, new_name)
        if not os.path.isdir(src_folder):
            print("ไม่เจอโฟลเดอร์", src_folder)
            continue
        os.makedirs(out_folder, exist_ok=True)

        files = []
        for f in sorted(os.listdir(src_folder)):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                files.append(f)
        rng.shuffle(files)

        chosen = []     # ลายนิ้วมือของรูปที่เลือกไปแล้ว
        saved = 0
        skipped = 0
        for f in files:
            if saved >= EXTERNAL_PER_CLASS:
                break
            try:
                with Image.open(os.path.join(src_folder, f)) as im:
                    img = to_rgb(im)
            except Exception:
                skipped = skipped + 1      # รูปเสีย
                continue

            # ชุดนี้มีรูปหมุน/ใส่จุดซ้ำเยอะ ถ้าคล้ายรูปที่เลือกไปแล้ว ข้าม
            p = picture_print(img)
            same = False
            for q in chosen:
                if count_diff(p, q) <= SAME_PICTURE:
                    same = True
                    break
            if same:
                skipped = skipped + 1
                continue

            chosen.append(p)
            img.thumbnail((EXTERNAL_MAX_SIDE, EXTERNAL_MAX_SIDE))
            img.save(os.path.join(out_folder, new_name + "_" + str(saved + 1).zfill(3) + ".jpg"), quality=90)
            saved = saved + 1
        print(new_name, "เซฟ", saved, "รูป | ข้ามรูปซ้ำ/รูปเสีย", skipped)


# ===== เริ่มทำงาน =====
items = read_all_images()
print("เหลือรูปทั้งหมด", len(items), "รูป")
groups = make_groups(items)
big = 0
for g in groups:
    if len(g) > 1:
        big = big + 1
print("จับกลุ่มรูปที่คล้ายกันได้", len(groups), "กลุ่ม (กลุ่มที่มีมากกว่า 1 รูป:", big, ")")
splits = split_groups(groups)
write_dataset(splits)
print("เสร็จส่วนที่ 1 ชุดเทรนอยู่ที่", os.path.abspath(OUT_DIR))

if os.path.isdir(KAGGLE_DIR):
    make_external_test()
    print("เสร็จส่วนที่ 2 ชุดทดสอบภายนอกอยู่ที่", os.path.abspath(EXTERNAL_DIR))
else:
    print("ไม่มีโฟลเดอร์ Kaggle ข้ามส่วนที่ 2 (ชุดทดสอบภายนอก)")
