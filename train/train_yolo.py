# เทรน YOLOv8 ตีกรอบผลไม้ 5 ชนิด บอกสด (Good) / เน่า (Bad) แล้ววัดผล
# การทดลองตาม Model Tuning ของโจทย์ CS461 : scratch vs pretrained / SGD vs Adam vs RMSProp /
#   LR คงที่ vs Cosine / batch 16 vs 32 / weight decay vs ไม่มี (ทุกตัวใช้ Early Stopping)
# ผลที่ได้ : models/ (เอาไปใส่ web/models/) และ results/ (กราฟ ตาราง)
# วิธีรัน : python train_yolo.py --data datasets/data_5fruits/data.yaml --out โฟลเดอร์ผล
#   ตัวเลือก : --external --more-data --only --new-test --same-source-test --team-test --compare --quick
#   คำสั่งของแต่ละรอบดูใน docs/train-model.md และโน้ตบุ๊ก train_roundN.ipynb

import os
import sys
import csv
import json
import time
import shutil
import torch
import ultralytics
from ultralytics import YOLO
import matplotlib
matplotlib.use("Agg")   # วาดกราฟลงไฟล์ ไม่ต้องเปิดหน้าต่าง
import matplotlib.pyplot as plt
plt.rcParams["lines.marker"] = "."   # ใส่จุดทุก epoch (การทดลองที่หยุดเร็วจะยังเห็นเส้น)


# ===== ตั้งค่า =====
DATA_YAML = "datasets/data_5fruits/data.yaml"
OUT_DIR = "."

IMG_SIZE = 640          # ขนาดรูปเข้าโมเดล
EPOCHS = 60             # รอบสูงสุด
PATIENCE = 10           # Early Stopping : val ไม่ดีขึ้น 10 รอบติด = หยุด
SEED = 42

EXTERNAL_DIR = ""       # ชุดทดสอบภายนอก (Kaggle) ไม่ใส่ = ข้าม
MORE_DATA = ""          # รอบ 2+ : ชุดเทรนเดิม + รูปเพิ่ม
ONLY = []               # รันแค่การทดลองที่ระบุ (ไม่ใส่ = ทั้งหมด)
NEW_TEST_DIR = ""       # รอบ 3 : ข้อสอบอิสระที่มีกรอบ
SAME_SOURCE_DIR = ""    # รอบ 3 : ข้อสอบชุดถ่ายเดียวกับชุดเทรน (ไม่ใช่ข้อสอบอิสระ)
COMPARE = {}            # โมเดลเก่าไว้เทียบ ชื่อ -> best.pt
TEAM_TEST_DIR = ""      # รอบ 4 : ข้อสอบชุดรูปที่ทีมรวบรวมเพิ่ม (ไม่มีกรอบ)

QUICK_TEST = False
for i in range(len(sys.argv)):
    if sys.argv[i] == "--data":
        DATA_YAML = sys.argv[i + 1]
    if sys.argv[i] == "--out":
        OUT_DIR = sys.argv[i + 1]
    if sys.argv[i] == "--external":
        EXTERNAL_DIR = sys.argv[i + 1]
    if sys.argv[i] == "--more-data":
        MORE_DATA = sys.argv[i + 1]
    if sys.argv[i] == "--only":
        ONLY = sys.argv[i + 1].split(",")
    if sys.argv[i] == "--new-test":
        NEW_TEST_DIR = sys.argv[i + 1]
    if sys.argv[i] == "--same-source-test":
        SAME_SOURCE_DIR = sys.argv[i + 1]
    if sys.argv[i] == "--compare":
        for pair in sys.argv[i + 1].split(","):
            name, path = pair.split("=")
            COMPARE[name.strip()] = path.strip()
    if sys.argv[i] == "--team-test":
        TEAM_TEST_DIR = sys.argv[i + 1]
    if sys.argv[i] == "--quick":
        QUICK_TEST = True

if QUICK_TEST:
    EPOCHS = 1
    IMG_SIZE = 320

MODEL_DIR = os.path.join(OUT_DIR, "models")
RESULT_DIR = os.path.join(OUT_DIR, "results")
RUN_DIR = os.path.join(OUT_DIR, "runs")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

# ใช้ GPU ถ้ามี
if torch.cuda.is_available():
    DEVICE = 0
else:
    DEVICE = "cpu"


# ===== รายการการทดลอง =====
# baseline = yolov8n.pt, SGD, lr 0.01 คงที่, batch 16, weight decay 0.0005 แต่ละการทดลองเปลี่ยนทีละอย่าง
#   model : yolov8n.yaml = เริ่มจากศูนย์ / yolov8n.pt = pretrained (COCO)
#   lrf : lr ตอนจบ = lr0 x lrf (1.0 = คงที่)
EXPERIMENTS = [
    {"name": "1_scratch_sgd", "model": "yolov8n.yaml", "optimizer": "SGD", "lr0": 0.01, "cos_lr": False, "lrf": 1.0, "batch": 16, "weight_decay": 0.0005},
    {"name": "2_pretrained_sgd", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": False, "lrf": 1.0, "batch": 16, "weight_decay": 0.0005},
    {"name": "3_adam", "model": "yolov8n.pt", "optimizer": "Adam", "lr0": 0.001, "cos_lr": False, "lrf": 1.0, "batch": 16, "weight_decay": 0.0005},
    {"name": "4_rmsprop", "model": "yolov8n.pt", "optimizer": "RMSProp", "lr0": 0.001, "cos_lr": False, "lrf": 1.0, "batch": 16, "weight_decay": 0.0005},
    {"name": "5_cosine_lr", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005},
    {"name": "6_batch32", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": False, "lrf": 1.0, "batch": 32, "weight_decay": 0.0005},
    {"name": "7_no_weight_decay", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": False, "lrf": 1.0, "batch": 16, "weight_decay": 0.0},
    # รอบ 2 : ค่าเดียวกับ 5 แต่เพิ่มรูป Kaggle เข้าชุดเทรน
    {"name": "8_cosine_more_data", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005, "more_data": True},
    # รอบ 2 : RMSProp lr 0.001 loss พุ่ง ลองลด lr 10 เท่า
    {"name": "9_rmsprop_low_lr", "model": "yolov8n.pt", "optimizer": "RMSProp", "lr0": 0.0001, "cos_lr": False, "lrf": 1.0, "batch": 16, "weight_decay": 0.0005},
    # รอบ 3 : ค่าเดียวกับ 8 + ส้มเน่า เทรนซ้ำ 3 seed ดูว่าผลแกว่งแค่ไหน
    {"name": "10_new_data", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005, "more_data": True, "seed": 42},
    {"name": "11_new_data_seed2", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005, "more_data": True, "seed": 2},
    {"name": "12_new_data_seed3", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005, "more_data": True, "seed": 3},
    # รอบ 4 : ค่าเดียวกับ 10-12 + รูปมะนาว/ทับทิมของทีม (kaggle_boxes_v4)
    {"name": "13_team_data", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005, "more_data": True, "seed": 42},
    {"name": "14_team_data_seed2", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005, "more_data": True, "seed": 2},
    {"name": "15_team_data_seed3", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005, "more_data": True, "seed": 3},
]
SEED_RUNS = ["10_new_data", "11_new_data_seed2", "12_new_data_seed3"]
SEED_RUNS_4 = ["13_team_data", "14_team_data_seed2", "15_team_data_seed3"]


# ===== อ่านชื่อคลาสจาก data.yaml =====
def read_class_names():
    for line in open(DATA_YAML, encoding="utf-8"):
        if line.startswith("names:"):
            text = line.split(":", 1)[1].strip().strip("[]")
            names = []
            for n in text.split(","):
                names.append(n.strip().strip("'\""))
            return names
    return []


CLASS_NAMES = read_class_names()


# ===== อ่าน results.csv ที่ YOLO เขียนไว้ทุก epoch =====
# บางรุ่นชื่อคอลัมน์มีช่องว่างนำหน้า เลยตัดออก
def read_history(name):
    file = os.path.join(RUN_DIR, name, "results.csv")
    history = {}
    if not os.path.exists(file):
        return history
    with open(file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for key in row:
                clean_key = key.strip()
                if clean_key not in history:
                    history[clean_key] = []
                history[clean_key].append(float(row[key]))
    # รวม loss 3 ส่วน (กรอบ + คลาส + ขอบ) เป็นตัวเดียว
    for part in ["train", "val"]:
        box = history.get(part + "/box_loss")
        cls = history.get(part + "/cls_loss")
        dfl = history.get(part + "/dfl_loss")
        if box and cls and dfl:
            total = []
            for i in range(len(box)):
                total.append(box[i] + cls[i] + dfl[i])
            history[part + "/total_loss"] = total
    return history


# ===== วาดกราฟ =====
def plot_history(name):
    h = read_history(name)
    if "epoch" not in h:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(h["epoch"], h["train/total_loss"], label="train")
    axes[0].plot(h["epoch"], h["val/total_loss"], label="validation")
    axes[0].set_title(name + " : Loss")
    axes[0].set_yscale("log")   # สเกล log : loss ที่พุ่งสูงจะไม่ทำให้เส้นอื่นแบน
    axes[0].set_xlabel("epoch")
    axes[0].legend()
    axes[1].plot(h["epoch"], h["metrics/mAP50(B)"], label="mAP50")
    axes[1].plot(h["epoch"], h["metrics/precision(B)"], label="precision")
    axes[1].plot(h["epoch"], h["metrics/recall(B)"], label="recall")
    axes[1].set_title(name + " : Validation score")
    axes[1].set_xlabel("epoch")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULT_DIR, "curves_" + name + ".png"), dpi=150)
    plt.close(fig)


def plot_compare(names, file_name, title):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for name in names:
        h = read_history(name)
        if "epoch" not in h:
            continue
        axes[0].plot(h["epoch"], h["val/total_loss"], label=name)
        axes[1].plot(h["epoch"], h["metrics/mAP50(B)"], label=name)
    axes[0].set_title(title + " : Validation Loss")
    axes[0].set_yscale("log")   # สเกล log (RMSProp เคย loss พุ่งไป 4 หมื่น)
    axes[1].set_title(title + " : Validation mAP50")
    for ax in axes:
        ax.set_xlabel("epoch")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULT_DIR, file_name), dpi=150)
    plt.close(fig)


# ===== ตารางสรุป (ทำต่อจากที่ค้างได้) =====
SUMMARY_FILE = os.path.join(RESULT_DIR, "summary.csv")
SUMMARY_HEAD = ["name", "start_from", "optimizer", "lr0", "lr_schedule", "batch", "weight_decay", "epochs_run",
                "val_mAP50", "test_precision", "test_recall", "test_f1", "test_mAP50", "test_mAP50_95", "minutes"]


def read_summary():
    rows = []
    if os.path.exists(SUMMARY_FILE):
        with open(SUMMARY_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(row)
    return rows


def write_summary(rows):
    with open(SUMMARY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_HEAD)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def f1_score(p, r):
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


# ===== เทรน 1 การทดลอง =====
def run_experiment(exp):
    print("\n========== เริ่ม", exp["name"], "==========")
    start = time.time()
    model = YOLO(exp["model"])
    # การทดลองที่มี more_data ใช้ชุดเทรนที่เพิ่มรูป
    train_data = DATA_YAML
    if "more_data" in exp:
        train_data = MORE_DATA
    model.train(
        data=train_data,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=exp["batch"],
        optimizer=exp["optimizer"],
        lr0=exp["lr0"],
        lrf=exp["lrf"],
        cos_lr=exp["cos_lr"],
        weight_decay=exp["weight_decay"],
        patience=PATIENCE,
        seed=exp.get("seed", SEED),   # ไม่ตั้ง seed = 42
        deterministic=True,
        device=DEVICE,
        workers=2,
        fraction=0.1 if QUICK_TEST else 1.0,   # ตอนทดสอบโค้ดใช้รูปแค่ 10%
        project=os.path.abspath(RUN_DIR),
        name=exp["name"],
        exist_ok=True,
        plots=True,
        verbose=False,
    )
    minutes = (time.time() - start) / 60

    # วัดผลด้วย best.pt ของการทดลองนี้
    best_path = os.path.join(RUN_DIR, exp["name"], "weights", "best.pt")
    best = YOLO(best_path)
    val_m = best.val(data=DATA_YAML, split="val", imgsz=IMG_SIZE, device=DEVICE,
                     project=os.path.abspath(RUN_DIR), name=exp["name"] + "_val", exist_ok=True, verbose=False)
    test_m = best.val(data=DATA_YAML, split="test", imgsz=IMG_SIZE, device=DEVICE,
                      project=os.path.abspath(RUN_DIR), name=exp["name"] + "_test", exist_ok=True, verbose=False)

    p = float(test_m.box.mp)
    r = float(test_m.box.mr)
    plot_history(exp["name"])
    h = read_history(exp["name"])
    row = {
        "name": exp["name"],
        "start_from": "scratch" if exp["model"].endswith(".yaml") else "pretrained",
        "optimizer": exp["optimizer"], "lr0": exp["lr0"],
        "lr_schedule": "cosine" if exp["cos_lr"] else "fixed",
        "batch": exp["batch"], "weight_decay": exp["weight_decay"],
        "epochs_run": len(h.get("epoch", [])),
        "val_mAP50": round(float(val_m.box.map50), 4),
        "test_precision": round(p, 4), "test_recall": round(r, 4), "test_f1": round(f1_score(p, r), 4),
        "test_mAP50": round(float(test_m.box.map50), 4), "test_mAP50_95": round(float(test_m.box.map), 4),
        "minutes": round(minutes, 1),
    }
    print(exp["name"], "| val mAP50", row["val_mAP50"], "| test P", row["test_precision"], "R", row["test_recall"],
          "F1", row["test_f1"], "mAP50", row["test_mAP50"], "|", row["minutes"], "นาที")
    return row, best_path, test_m


# ===== บันทึกโมเดลที่ดีที่สุด (เลือกจาก val mAP50 ไม่ใช่ test) =====
def save_best(row, best_path, test_m):
    shutil.copy(best_path, os.path.join(MODEL_DIR, "best_detect.pt"))

    # คะแนนรายคลาสบน test
    with open(os.path.join(RESULT_DIR, "per_class_best.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["class", "precision", "recall", "f1", "mAP50"])
        for i in range(len(test_m.box.ap_class_index)):
            k = int(test_m.box.ap_class_index[i])
            p = float(test_m.box.p[i])
            r = float(test_m.box.r[i])
            writer.writerow([CLASS_NAMES[k], round(p, 4), round(r, 4), round(f1_score(p, r), 4), round(float(test_m.box.ap50[i]), 4)])

    # ก๊อป Confusion Matrix ของ test
    test_folder = os.path.join(RUN_DIR, row["name"] + "_test")
    for f in ["confusion_matrix.png", "confusion_matrix_normalized.png"]:
        if os.path.exists(os.path.join(test_folder, f)):
            shutil.copy(os.path.join(test_folder, f), os.path.join(RESULT_DIR, f.replace(".png", "_best.png")))
    print(">>> โมเดลที่ดีที่สุดตอนนี้:", row["name"])


# ===== สอบรูปที่ไม่มีกรอบ (Kaggle / ชุดของทีม) =====
# ใช้ชื่อโฟลเดอร์เป็นคำตอบ เทียบกับกรอบที่โมเดลมั่นใจที่สุดในรูป
# tag = ชื่อโมเดล / test_dir = โฟลเดอร์ข้อสอบ / prefix = คำนำหน้าชื่อไฟล์ผล
def test_external(model_path, tag, test_dir="", prefix="external"):
    if test_dir == "":
        test_dir = EXTERNAL_DIR
    model = YOLO(model_path)
    rows = []
    table = {}   # table[ของจริง][ที่โมเดลทาย] = จำนวนรูป
    all_count = 0
    right_class = 0
    right_fruit = 0
    right_fresh = 0
    not_found = 0
    rotten_count = 0
    rotten_fresh = 0     # ลูกเน่าที่โมเดลบอกว่าสด
    for true_name in sorted(os.listdir(test_dir)):
        folder = os.path.join(test_dir, true_name)
        if not os.path.isdir(folder) or true_name not in CLASS_NAMES:
            continue
        images = []
        for f in sorted(os.listdir(folder)):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                images.append(os.path.join(folder, f))
        if len(images) == 0:     # คลาสที่ไม่มีรูป ข้าม
            continue
        table[true_name] = {}
        hit = 0
        for r in model.predict(images, imgsz=IMG_SIZE, conf=0.25, device=DEVICE, stream=True, verbose=False):
            if len(r.boxes) == 0:
                guess = "not_found"
            else:
                top = int(r.boxes.conf.argmax())
                guess = CLASS_NAMES[int(r.boxes.cls[top])]
            table[true_name][guess] = table[true_name].get(guess, 0) + 1
            all_count = all_count + 1
            if guess == true_name:
                hit = hit + 1
                right_class = right_class + 1
            if guess.split("_")[0] == true_name.split("_")[0]:
                right_fruit = right_fruit + 1
            if guess != "not_found" and guess.split("_")[1] == true_name.split("_")[1]:
                right_fresh = right_fresh + 1
            if guess == "not_found":
                not_found = not_found + 1
            if true_name.endswith("_Bad"):
                rotten_count = rotten_count + 1
                if guess.endswith("_Good"):
                    rotten_fresh = rotten_fresh + 1
        rows.append([true_name, len(images), hit, round(hit / max(len(images), 1), 4)])

    with open(os.path.join(RESULT_DIR, prefix + "_" + tag + "_accuracy.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["class", "images", "correct", "accuracy"])
        for row in rows:
            writer.writerow(row)
    # ตาราง แถว = ของจริง คอลัมน์ = ที่โมเดลทาย
    columns = CLASS_NAMES + ["not_found"]
    with open(os.path.join(RESULT_DIR, prefix + "_" + tag + "_confusion.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["actual \\ predicted"] + columns)
        for true_name in table:
            row = [true_name]
            for c in columns:
                row.append(table[true_name].get(c, 0))
            writer.writerow(row)
    summary_file = os.path.join(RESULT_DIR, prefix + "_" + tag + "_summary.txt")
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(prefix + " " + tag + " (รูปที่โมเดลไม่เคยเห็น)\n")
        f.write("จำนวนรูป " + str(all_count) + "\n")
        f.write("ทายถูกทั้งชนิดและสด/เน่า " + str(round(right_class / max(all_count, 1), 4)) + "\n")
        f.write("ทายชนิดผลไม้ถูก " + str(round(right_fruit / max(all_count, 1), 4)) + "\n")
        f.write("ทายสด/เน่าถูก " + str(round(right_fresh / max(all_count, 1), 4)) + "\n")
        f.write("หาผลไม้ไม่เจอ " + str(not_found) + " รูป\n")
        f.write("ลูกเน่าที่บอกว่าสด " + str(rotten_fresh) + " / " + str(rotten_count) + " รูป\n")
    print(open(summary_file, encoding="utf-8").read())
    return {"model": tag, "images": all_count,
            "accuracy": round(right_class / max(all_count, 1), 4),
            "fruit_correct": round(right_fruit / max(all_count, 1), 4),
            "fresh_rotten_correct": round(right_fresh / max(all_count, 1), 4),
            "not_found": not_found, "rotten_called_fresh": rotten_fresh, "rotten_images": rotten_count}


# ===== สอบข้อสอบที่มีกรอบ (รอบ 3) =====
# เขียน data.yaml ให้ YOLO อ่านโฟลเดอร์ images/ labels/
def make_test_yaml(folder):
    yaml_file = os.path.join(folder, "data.yaml")
    names_text = ", ".join("'" + n + "'" for n in CLASS_NAMES)
    with open(yaml_file, "w", encoding="utf-8") as f:
        f.write("path: " + os.path.abspath(folder) + "\n")
        f.write("train: images\nval: images\ntest: images\n")
        f.write("nc: " + str(len(CLASS_NAMES)) + "\n")
        f.write("names: [" + names_text + "]\n")
    return yaml_file


NEW_TEST_FILE = os.path.join(RESULT_DIR, "new_tests.csv")
NEW_TEST_HEAD = ["model", "test_set", "images", "precision", "recall", "f1", "mAP50", "rotten_called_fresh"]


def read_new_tests():
    rows = []
    if os.path.exists(NEW_TEST_FILE):
        with open(NEW_TEST_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(row)
    return rows


# วัดผล 1 โมเดล x ข้อสอบ 1 ชุด : P R F1 mAP50 + รายคลาส + ลูกเน่าที่บอกว่าสด
def test_detect(model_path, folder, model_name, set_name):
    yaml_file = make_test_yaml(folder)
    images = len(os.listdir(os.path.join(folder, "images")))
    m = YOLO(model_path).val(data=yaml_file, split="test", imgsz=IMG_SIZE, device=DEVICE,
                             project=os.path.abspath(RUN_DIR), name=model_name + "_" + set_name,
                             exist_ok=True, verbose=False)
    p = float(m.box.mp)
    r = float(m.box.mr)

    # Confusion matrix ของ YOLO : แถว = ที่ทาย, คอลัมน์ = ของจริง
    # ลูกเน่าที่บอกว่าสด = แถว X_Good คอลัมน์ X_Bad (อันตรายสุด หลุดถึงลูกค้า)
    matrix = m.confusion_matrix.matrix
    rotten_fresh = 0
    for k in range(len(CLASS_NAMES)):
        if CLASS_NAMES[k].endswith("_Bad"):
            good = CLASS_NAMES.index(CLASS_NAMES[k].replace("_Bad", "_Good"))
            rotten_fresh = rotten_fresh + int(matrix[good][k])

    with open(os.path.join(RESULT_DIR, "per_class_" + model_name + "_" + set_name + ".csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["class", "precision", "recall", "f1", "mAP50"])
        for i in range(len(m.box.ap_class_index)):
            k = int(m.box.ap_class_index[i])
            pk = float(m.box.p[i])
            rk = float(m.box.r[i])
            writer.writerow([CLASS_NAMES[k], round(pk, 4), round(rk, 4), round(f1_score(pk, rk), 4), round(float(m.box.ap50[i]), 4)])

    row = {"model": model_name, "test_set": set_name, "images": images,
           "precision": round(p, 4), "recall": round(r, 4), "f1": round(f1_score(p, r), 4),
           "mAP50": round(float(m.box.map50), 4), "rotten_called_fresh": rotten_fresh}
    print(model_name, "|", set_name, "| F1", row["f1"], "mAP50", row["mAP50"], "| ลูกเน่าที่บอกว่าสด", rotten_fresh)
    return row


# ===== เทรนซ้ำ 3 seed ผลแกว่งแค่ไหน =====
def mean_and_spread(values):
    mean = sum(values) / len(values)
    spread = (max(values) - min(values)) / 2     # เขียนเป็น ค่าเฉลี่ย ± ครึ่งช่วง
    return round(mean, 4), round(spread, 4)


# runs = 3 seed ของรอบนั้น / team_rows = ผลชุดของทีม (รอบ 4)
def write_seed_summary(summary, new_rows, runs=SEED_RUNS, file_name="seed_summary.md", team_rows=[]):
    rows = []
    for r in summary:
        if r["name"] in runs:
            rows.append(r)
    if len(rows) < 2:
        return
    lines = ["| ค่าที่วัด | " + " | ".join(r["name"] for r in rows) + " | ค่าเฉลี่ย ± ครึ่งช่วง |",
             "|---|" + "---|" * len(rows) + "---|"]
    for key, label in [("val_mAP50", "Val mAP50"), ("test_f1", "Test F1"), ("test_mAP50", "Test mAP50")]:
        values = [float(r[key]) for r in rows]
        mean, spread = mean_and_spread(values)
        lines.append("| " + label + " | " + " | ".join(str(v) for v in values) + " | " + str(mean) + " ± " + str(spread) + " |")
    for set_name in ["new_test", "same_source_test"]:
        values = []
        for r in rows:
            for n in new_rows:
                if n["model"] == r["name"] and n["test_set"] == set_name:
                    values.append(float(n["f1"]))
        if len(values) == len(rows):
            mean, spread = mean_and_spread(values)
            lines.append("| F1 " + set_name + " | " + " | ".join(str(v) for v in values) + " | " + str(mean) + " ± " + str(spread) + " |")
    values = []
    for r in rows:
        for t in team_rows:
            if t["model"] == r["name"]:
                values.append(float(t["accuracy"]))
    if len(team_rows) > 0 and len(values) == len(rows):
        mean, spread = mean_and_spread(values)
        lines.append("| ทายถูก team_collected_test | " + " | ".join(str(v) for v in values) + " | " + str(mean) + " ± " + str(spread) + " |")
    with open(os.path.join(RESULT_DIR, file_name), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


# ===== เริ่มทำงาน =====
print("ultralytics", ultralytics.__version__, "| torch", torch.__version__, "| device", DEVICE)
if DEVICE == "cpu":
    print("!!! ไม่เจอ GPU จะเทรนช้ามาก ใน Colab ให้ไปที่ Runtime > Change runtime type > เลือก GPU")
print("คลาส:", CLASS_NAMES)
with open(os.path.join(RESULT_DIR, "versions.txt"), "w", encoding="utf-8") as f:
    f.write("ultralytics " + ultralytics.__version__ + "\ntorch " + torch.__version__ + "\n")

# ทำต่อจากที่ค้างได้ (Colab หลุด รันใหม่ การทดลองที่เสร็จแล้วจะข้าม)
summary = read_summary()
done = []
for r in summary:
    done.append(r["name"])
best_score = -1.0
best_name = ""
for r in summary:
    if float(r["val_mAP50"]) > best_score:
        best_score = float(r["val_mAP50"])
        best_name = r["name"]

for exp in EXPERIMENTS:
    if len(ONLY) > 0 and exp["name"] not in ONLY:
        continue
    if "more_data" in exp and MORE_DATA == "":
        continue
    if exp["name"] in done:
        print("ข้าม", exp["name"], "(ทำเสร็จแล้ว)")
        continue
    row, best_path, test_m = run_experiment(exp)
    summary.append(row)
    write_summary(summary)   # บันทึกทุกครั้ง หลุดกลางทางไม่เสียผล
    if row["val_mAP50"] > best_score:
        best_score = row["val_mAP50"]
        best_name = row["name"]
        save_best(row, best_path, test_m)

# จดว่าเลือกโมเดลจากการทดลองไหน (เว็บอ่านคู่กับ best_detect.pt)
info = {
    "class_names": CLASS_NAMES,
    "img_size": IMG_SIZE,
    "chosen_experiment": best_name,
    "ultralytics_version": ultralytics.__version__,
}
with open(os.path.join(MODEL_DIR, "class_info.json"), "w", encoding="utf-8") as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

# สอบ Kaggle ทุกการทดลองที่เสร็จ (ทำแล้วข้าม)
if EXTERNAL_DIR != "" and os.path.isdir(EXTERNAL_DIR):
    for r in summary:
        done_file = os.path.join(RESULT_DIR, "external_" + r["name"] + "_summary.txt")
        best_file = os.path.join(RUN_DIR, r["name"], "weights", "best.pt")
        if os.path.exists(best_file) and not os.path.exists(done_file):
            test_external(best_file, r["name"])
    # โมเดลเก่าก็สอบด้วย
    for name in COMPARE:
        done_file = os.path.join(RESULT_DIR, "external_" + name + "_summary.txt")
        if os.path.exists(COMPARE[name]) and not os.path.exists(done_file):
            test_external(COMPARE[name], name)

# รอบ 3 : สอบข้อสอบที่มีกรอบ (คู่ไหนสอบแล้วข้าม)
new_rows = read_new_tests()
test_sets = {}
if NEW_TEST_DIR != "" and os.path.isdir(NEW_TEST_DIR):
    test_sets["new_test"] = NEW_TEST_DIR
if SAME_SOURCE_DIR != "" and os.path.isdir(SAME_SOURCE_DIR):
    test_sets["same_source_test"] = SAME_SOURCE_DIR
# โมเดลที่จะสอบ = --compare + ทุกการทดลองที่เสร็จ
models = {}
for name in COMPARE:
    if os.path.exists(COMPARE[name]):
        models[name] = COMPARE[name]
    else:
        print("ไม่เจอไฟล์โมเดล", COMPARE[name], "ข้าม", name)
for r in summary:
    best_file = os.path.join(RUN_DIR, r["name"], "weights", "best.pt")
    if os.path.exists(best_file):
        models[r["name"]] = best_file
if len(test_sets) > 0:
    for name in models:
        for set_name in test_sets:
            done = False
            for n in new_rows:
                if n["model"] == name and n["test_set"] == set_name:
                    done = True
            if done:
                continue
            new_rows.append(test_detect(models[name], test_sets[set_name], name, set_name))
            with open(NEW_TEST_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=NEW_TEST_HEAD)
                writer.writeheader()
                for n in new_rows:
                    writer.writerow(n)

# รอบ 4 : สอบชุดของทีม ทุกโมเดล (ทำแล้วข้าม)
TEAM_TEST_FILE = os.path.join(RESULT_DIR, "team_tests.csv")
TEAM_TEST_HEAD = ["model", "images", "accuracy", "fruit_correct", "fresh_rotten_correct", "not_found", "rotten_called_fresh", "rotten_images"]
team_rows = []
if os.path.exists(TEAM_TEST_FILE):
    with open(TEAM_TEST_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            team_rows.append(row)
if TEAM_TEST_DIR != "" and os.path.isdir(TEAM_TEST_DIR):
    for name in models:
        done = False
        for t in team_rows:
            if t["model"] == name:
                done = True
        if done:
            continue
        team_rows.append(test_external(models[name], name, TEAM_TEST_DIR, "team_test"))
        with open(TEAM_TEST_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=TEAM_TEST_HEAD)
            writer.writeheader()
            for t in team_rows:
                writer.writerow(t)

write_seed_summary(summary, new_rows)
write_seed_summary(summary, new_rows, SEED_RUNS_4, "seed_summary_round4.md", team_rows)

# กราฟเปรียบเทียบไว้ใส่รายงาน
plot_compare(["1_scratch_sgd", "2_pretrained_sgd"], "compare_scratch_vs_pretrained.png", "Scratch vs Pretrained")
plot_compare(["2_pretrained_sgd", "3_adam", "4_rmsprop"], "compare_optimizers.png", "SGD vs Adam vs RMSProp")
plot_compare(["2_pretrained_sgd", "5_cosine_lr"], "compare_lr_fixed_vs_cosine.png", "LR fixed vs Cosine")
plot_compare(["2_pretrained_sgd", "6_batch32"], "compare_batch16_vs_32.png", "Batch 16 vs 32")
plot_compare(["2_pretrained_sgd", "7_no_weight_decay"], "compare_weight_decay.png", "Weight decay (L2) vs none")
plot_compare(["5_cosine_lr", "8_cosine_more_data"], "compare_more_data.png", "Original data vs + Kaggle images")
plot_compare(["4_rmsprop", "9_rmsprop_low_lr"], "compare_rmsprop_lr.png", "RMSProp lr 0.001 vs 0.0001")
plot_compare(SEED_RUNS, "compare_seeds.png", "Same settings, 3 seeds")
plot_compare(SEED_RUNS_4, "compare_seeds_round4.png", "Round 4 (+ team-collected images), 3 seeds")
all_names = []
for e in EXPERIMENTS:
    all_names.append(e["name"])
plot_compare(all_names, "compare_all.png", "All experiments")

# ตารางสรุป (วางในรายงานได้)
with open(os.path.join(RESULT_DIR, "summary.md"), "w", encoding="utf-8") as f:
    f.write("| การทดลอง | เริ่มจาก | Optimizer | LR | Batch | Weight decay | Epoch | Val mAP50 | Test Precision | Test Recall | Test F1 | Test mAP50 |\n")
    f.write("|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    for r in summary:
        f.write("| " + " | ".join([str(r["name"]), str(r["start_from"]), str(r["optimizer"]),
                                    str(r["lr0"]) + " " + str(r["lr_schedule"]), str(r["batch"]), str(r["weight_decay"]),
                                    str(r["epochs_run"]), str(r["val_mAP50"]), str(r["test_precision"]),
                                    str(r["test_recall"]), str(r["test_f1"]), str(r["test_mAP50"])]) + " |\n")

print("\nเสร็จทั้งหมด โมเดลที่เลือก:", best_name, "| ดูผลใน", RESULT_DIR)
