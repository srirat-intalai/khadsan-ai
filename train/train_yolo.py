# เทรน YOLOv8 detect ตีกรอบผลไม้ 5 ชนิด แล้วบอกว่าสด (Good) หรือเน่า (Bad)
# ทำการทดลองตามแนวทาง Model Tuning ของโจทย์ CS461 ครบในไฟล์เดียว
#   1) baseline เทรนจากศูนย์ เทียบกับ fine-tune จากโมเดลที่เทรนมาแล้ว (pretrained)
#   2) เทียบ Optimizer: SGD vs Adam vs RMSProp
#   3) เทียบ Learning Rate: คงที่ vs ค่อยๆ ลดแบบ Cosine
#   4) เทียบ Batch Size 16 vs 32
#   5) Regularization: มี L2 (weight decay) vs ไม่มี
#   6) ทุกการทดลองใช้ Early Stopping
# แล้ววัดผลบน test set (Precision, Recall, F1, mAP50, Confusion Matrix)
#
# ผลที่ได้:
#   models/best_detect.pt, models/class_info.json  -> เอาไปใช้ในเว็บ (วางใน web/models/)
#   results/  -> กราฟ ตาราง ไว้ใส่รายงานกับสไลด์
#
# วิธีรัน:  python train_yolo.py --data datasets/data_5fruits/data.yaml --out โฟลเดอร์เก็บผล
# ทดสอบกับรูปจากแหล่งอื่นด้วย:  เติม --external datasets/external_test
# รอบ 2 (เพิ่มรูป Kaggle + แก้ RMSProp) :  เติม --more-data datasets/data_5fruits/data_more.yaml --only 5_cosine_lr,8_cosine_more_data,4_rmsprop,9_rmsprop_low_lr
# รอบ 3 (เพิ่มส้มเน่า + เทรนซ้ำ 3 seed + ข้อสอบใหม่) :
#   เติม --more-data ...data_more.yaml --only 10_new_data,11_new_data_seed2,12_new_data_seed3
#        --new-test datasets/new_test --same-source-test datasets/same_source_test
#        --compare "5_cosine_lr=ที่อยู่best.pt,8_cosine_more_data=ที่อยู่best.pt"   (โมเดลเก่าที่อยากสอบข้อสอบใหม่ด้วย ไม่ต้องเทรนใหม่)
# ทดสอบโค้ดเร็วๆ (รูปน้อย 1 epoch):  เติม --quick

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
plt.rcParams["lines.marker"] = "."   # ใส่จุดทุก epoch การทดลองที่หยุดเร็วจะได้ยังเห็นเส้น


# ===== ตั้งค่า =====
DATA_YAML = "datasets/data_5fruits/data.yaml"
OUT_DIR = "."

IMG_SIZE = 640          # ขนาดรูปเข้าโมเดล (ค่ามาตรฐานของ YOLO detect)
EPOCHS = 60             # รอบสูงสุด
PATIENCE = 10           # Early Stopping: ถ้าคะแนน validation ไม่ดีขึ้น 10 รอบติด ให้หยุด
SEED = 42

EXTERNAL_DIR = ""       # ชุดทดสอบภายนอก (prepare_data.py ส่วนที่ 2 ทำไว้) ไม่ใส่ = ข้าม
MORE_DATA = ""          # รอบ 2 : data_more.yaml (ชุดเทรนเดิม + รูป Kaggle) ไม่ใส่ = ข้ามการทดลองที่ 8
ONLY = []               # รันแค่การทดลองที่ระบุ เช่น --only 5_cosine_lr,8_cosine_more_data (ไม่ใส่ = รันทั้งหมด)
NEW_TEST_DIR = ""       # รอบ 3 : ข้อสอบใหม่ที่มีกรอบ จากแหล่งที่ไม่ได้ใช้เทรนเลย (images/ + labels/)
SAME_SOURCE_DIR = ""    # รอบ 3 : ข้อสอบที่มาจากชุดถ่ายเดียวกับชุดเทรน แต่คนละรูป (ดูประกอบ ไม่ใช่ข้อสอบอิสระ)
COMPARE = {}            # รอบ 3 : โมเดลเก่าที่อยากสอบข้อสอบใหม่ด้วย ชื่อ -> ที่อยู่ไฟล์ best.pt

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
# baseline (ข้อ 2) = เริ่มจาก yolov8n.pt, SGD, lr 0.01 คงที่, batch 16, weight decay 0.0005
# แต่ละการทดลองเปลี่ยนทีละอย่างจาก baseline จะได้รู้ว่าอะไรมีผล
#   model: yolov8n.yaml = โครงเปล่า เทรนจากศูนย์ / yolov8n.pt = โมเดลที่เทรนกับรูปทั่วไป (COCO) มาแล้ว
#   lrf: lr ตอนจบ = lr0 x lrf  (1.0 = คงที่ตลอด)
EXPERIMENTS = [
    {"name": "1_scratch_sgd", "model": "yolov8n.yaml", "optimizer": "SGD", "lr0": 0.01, "cos_lr": False, "lrf": 1.0, "batch": 16, "weight_decay": 0.0005},
    {"name": "2_pretrained_sgd", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": False, "lrf": 1.0, "batch": 16, "weight_decay": 0.0005},
    {"name": "3_adam", "model": "yolov8n.pt", "optimizer": "Adam", "lr0": 0.001, "cos_lr": False, "lrf": 1.0, "batch": 16, "weight_decay": 0.0005},
    {"name": "4_rmsprop", "model": "yolov8n.pt", "optimizer": "RMSProp", "lr0": 0.001, "cos_lr": False, "lrf": 1.0, "batch": 16, "weight_decay": 0.0005},
    {"name": "5_cosine_lr", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005},
    {"name": "6_batch32", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": False, "lrf": 1.0, "batch": 32, "weight_decay": 0.0005},
    {"name": "7_no_weight_decay", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": False, "lrf": 1.0, "batch": 16, "weight_decay": 0.0},
    # รอบ 2 : ค่าเดียวกับตัวที่ดีที่สุด (5_cosine_lr) แต่ชุดเทรนเพิ่มรูป Kaggle (val/test ชุดเดิม เทียบกันได้ยุติธรรม)
    {"name": "8_cosine_more_data", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005, "more_data": True},
    # รอบ 2 : รอบแรก RMSProp (lr 0.001) loss พุ่งไปหลักหมื่นแล้วคะแนนแกว่งตลอด ลองลด lr ลง 10 เท่า ดูว่านิ่งขึ้นไหม
    {"name": "9_rmsprop_low_lr", "model": "yolov8n.pt", "optimizer": "RMSProp", "lr0": 0.0001, "cos_lr": False, "lrf": 1.0, "batch": 16, "weight_decay": 0.0005},
    # รอบ 3 : ค่าเดียวกับ 8 แต่ชุดเทรนเพิ่มส้มเน่า (rotten_orange) แล้วเทรนซ้ำ 3 ครั้งด้วย seed ต่างกัน
    # รอบ 1-2 ล็อก seed 42 ไว้ รันซ้ำก็ได้เลขเดิม เลยไม่รู้ว่าคะแนนแกว่งได้แค่ไหน 3 seed นี้จะบอกว่าผลนิ่งจริงไหม
    {"name": "10_new_data", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005, "more_data": True, "seed": 42},
    {"name": "11_new_data_seed2", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005, "more_data": True, "seed": 2},
    {"name": "12_new_data_seed3", "model": "yolov8n.pt", "optimizer": "SGD", "lr0": 0.01, "cos_lr": True, "lrf": 0.01, "batch": 16, "weight_decay": 0.0005, "more_data": True, "seed": 3},
]
SEED_RUNS = ["10_new_data", "11_new_data_seed2", "12_new_data_seed3"]


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
# บางรุ่นของ ultralytics ชื่อคอลัมน์มีช่องว่างนำหน้า เลยตัดช่องว่างออกก่อน
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
    # รวม loss 3 ส่วนของ YOLO (กรอบ + คลาส + ขอบ) เป็นตัวเดียว ให้อ่านง่าย
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
    axes[0].set_yscale("log")   # สเกล log : ถ้ามีการทดลองไหน loss พุ่งสูงมาก เส้นอื่นจะไม่แบนติดศูนย์
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
    axes[0].set_yscale("log")   # สเกล log : RMSProp เคย loss พุ่งไป 4 หมื่น ถ้าไม่ใช้ log เส้นอื่นแบนจนอ่านไม่ได้
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
    # ข้อมูลที่ใช้เทรน : การทดลองที่ 8 ใช้ชุดที่เพิ่มรูป Kaggle นอกนั้นใช้ชุดเดิม
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
        seed=exp.get("seed", SEED),   # รอบ 3 แต่ละการทดลองตั้ง seed เองได้ ไม่ตั้ง = 42 เหมือนรอบก่อน
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

    # วัดผลด้วยโมเดลตัวที่ดีที่สุดของการทดลองนี้ (best.pt)
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


# ===== บันทึกโมเดลที่ดีที่สุด (เลือกจาก val mAP50 ไม่ใช่ test เพื่อความยุติธรรม) =====
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

    # ก๊อปกราฟ Confusion Matrix ที่ YOLO วาดให้ตอนวัดผล test
    test_folder = os.path.join(RUN_DIR, row["name"] + "_test")
    for f in ["confusion_matrix.png", "confusion_matrix_normalized.png"]:
        if os.path.exists(os.path.join(test_folder, f)):
            shutil.copy(os.path.join(test_folder, f), os.path.join(RESULT_DIR, f.replace(".png", "_best.png")))
    print(">>> โมเดลที่ดีที่สุดตอนนี้:", row["name"])


# ===== ทดสอบกับรูปจากแหล่งอื่น (external test) =====
# รูปพวกนี้ไม่มีกรอบ มีแค่ชื่อโฟลเดอร์บอกคำตอบ (เช่น Apple_Bad)
# เลยดูแค่กรอบที่โมเดลมั่นใจที่สุดในรูป ว่าบอกชนิดและสด/เน่าถูกไหม
# tag = ชื่อการทดลอง ใช้ตั้งชื่อไฟล์ผล จะได้เทียบได้หลายโมเดล
def test_external(model_path, tag):
    model = YOLO(model_path)
    rows = []
    table = {}   # table[ของจริง][ที่โมเดลทาย] = จำนวนรูป
    all_count = 0
    right_class = 0
    right_fruit = 0
    right_fresh = 0
    for true_name in sorted(os.listdir(EXTERNAL_DIR)):
        folder = os.path.join(EXTERNAL_DIR, true_name)
        if not os.path.isdir(folder) or true_name not in CLASS_NAMES:
            continue
        images = []
        for f in sorted(os.listdir(folder)):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                images.append(os.path.join(folder, f))
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
        rows.append([true_name, len(images), hit, round(hit / max(len(images), 1), 4)])

    with open(os.path.join(RESULT_DIR, "external_" + tag + "_accuracy.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["class", "images", "correct", "accuracy"])
        for row in rows:
            writer.writerow(row)
    # ตารางว่ารูปแต่ละคลาส โมเดลทายว่าอะไรบ้าง (แถว = ของจริง, คอลัมน์ = ที่โมเดลทาย)
    columns = CLASS_NAMES + ["not_found"]
    with open(os.path.join(RESULT_DIR, "external_" + tag + "_confusion.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["actual \\ predicted"] + columns)
        for true_name in table:
            row = [true_name]
            for c in columns:
                row.append(table[true_name].get(c, 0))
            writer.writerow(row)
    with open(os.path.join(RESULT_DIR, "external_" + tag + "_summary.txt"), "w", encoding="utf-8") as f:
        f.write("external test " + tag + " (Kaggle, รูปที่โมเดลไม่เคยเห็น)\n")
        f.write("จำนวนรูป " + str(all_count) + "\n")
        f.write("ทายถูกทั้งชนิดและสด/เน่า " + str(round(right_class / max(all_count, 1), 4)) + "\n")
        f.write("ทายชนิดผลไม้ถูก " + str(round(right_fruit / max(all_count, 1), 4)) + "\n")
        f.write("ทายสด/เน่าถูก " + str(round(right_fresh / max(all_count, 1), 4)) + "\n")
    print(open(os.path.join(RESULT_DIR, "external_" + tag + "_summary.txt"), encoding="utf-8").read())


# ===== รอบ 3 : สอบกับข้อสอบใหม่ที่มีกรอบ =====
# โฟลเดอร์ข้อสอบมีแค่ images/ กับ labels/ เลยเขียน data.yaml ให้ YOLO อ่านเอง (ใช้ชื่อคลาส 10 ตัวเดิม)
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


# วัดผล 1 โมเดล กับข้อสอบ 1 ชุด ได้ P R F1 mAP50 รวม + รายคลาส + จำนวนลูกเน่าที่โมเดลบอกว่าสด
def test_detect(model_path, folder, model_name, set_name):
    yaml_file = make_test_yaml(folder)
    images = len(os.listdir(os.path.join(folder, "images")))
    m = YOLO(model_path).val(data=yaml_file, split="test", imgsz=IMG_SIZE, device=DEVICE,
                             project=os.path.abspath(RUN_DIR), name=model_name + "_" + set_name,
                             exist_ok=True, verbose=False)
    p = float(m.box.mp)
    r = float(m.box.mr)

    # Confusion matrix ของ YOLO : แถว = ที่โมเดลทาย, คอลัมน์ = ของจริง
    # ลูกเน่าที่โมเดลบอกว่าสด = แถว X_Good คอลัมน์ X_Bad ของผลไม้ชนิดเดียวกัน (อันตรายสุด ของเน่าหลุดไปถึงลูกค้า)
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


# ===== รอบ 3 : เทรนซ้ำ 3 seed ผลแกว่งแค่ไหน =====
def mean_and_spread(values):
    mean = sum(values) / len(values)
    spread = (max(values) - min(values)) / 2     # ครึ่งหนึ่งของช่วงต่ำสุด-สูงสุด เขียนเป็น ค่าเฉลี่ย ± ตัวนี้
    return round(mean, 4), round(spread, 4)


def write_seed_summary(summary, new_rows):
    rows = []
    for r in summary:
        if r["name"] in SEED_RUNS:
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
    with open(os.path.join(RESULT_DIR, "seed_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


# ===== เริ่มทำงาน =====
print("ultralytics", ultralytics.__version__, "| torch", torch.__version__, "| device", DEVICE)
if DEVICE == "cpu":
    print("!!! ไม่เจอ GPU จะเทรนช้ามาก ใน Colab ให้ไปที่ Runtime > Change runtime type > เลือก GPU")
print("คลาส:", CLASS_NAMES)
with open(os.path.join(RESULT_DIR, "versions.txt"), "w", encoding="utf-8") as f:
    f.write("ultralytics " + ultralytics.__version__ + "\ntorch " + torch.__version__ + "\n")

# ทำต่อจากที่ค้างได้ (ถ้า Colab หลุดกลางทาง รันใหม่แล้วการทดลองที่เสร็จแล้วจะถูกข้าม)
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
    write_summary(summary)   # บันทึกทุกครั้ง หลุดกลางทางก็ไม่เสียผล
    if row["val_mAP50"] > best_score:
        best_score = row["val_mAP50"]
        best_name = row["name"]
        save_best(row, best_path, test_m)

# จดว่าโมเดลที่เลือกมาจากการทดลองไหน คลาสอะไรบ้าง (เว็บอ่านไฟล์นี้คู่กับ best_detect.pt)
info = {
    "class_names": CLASS_NAMES,
    "img_size": IMG_SIZE,
    "chosen_experiment": best_name,
    "ultralytics_version": ultralytics.__version__,
}
with open(os.path.join(MODEL_DIR, "class_info.json"), "w", encoding="utf-8") as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

# ทดสอบกับรูปจากแหล่งอื่น ทุกการทดลองที่เทรนเสร็จ (ไฟล์ไหนทำแล้วข้าม)
if EXTERNAL_DIR != "" and os.path.isdir(EXTERNAL_DIR):
    for r in summary:
        done_file = os.path.join(RESULT_DIR, "external_" + r["name"] + "_summary.txt")
        best_file = os.path.join(RUN_DIR, r["name"], "weights", "best.pt")
        if os.path.exists(best_file) and not os.path.exists(done_file):
            test_external(best_file, r["name"])
    # โมเดลเก่า (--compare) ก็สอบชุดเดียวกัน จะได้เทียบกันตรงๆ
    for name in COMPARE:
        done_file = os.path.join(RESULT_DIR, "external_" + name + "_summary.txt")
        if os.path.exists(COMPARE[name]) and not os.path.exists(done_file):
            test_external(COMPARE[name], name)

# รอบ 3 : สอบข้อสอบใหม่ ทั้งโมเดลที่เพิ่งเทรน และโมเดลเก่าที่ใส่ใน --compare (คู่ไหนสอบแล้วข้าม)
new_rows = read_new_tests()
test_sets = {}
if NEW_TEST_DIR != "" and os.path.isdir(NEW_TEST_DIR):
    test_sets["new_test"] = NEW_TEST_DIR
if SAME_SOURCE_DIR != "" and os.path.isdir(SAME_SOURCE_DIR):
    test_sets["same_source_test"] = SAME_SOURCE_DIR
if len(test_sets) > 0:
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
write_seed_summary(summary, new_rows)

# กราฟเปรียบเทียบไว้ใส่รายงาน
plot_compare(["1_scratch_sgd", "2_pretrained_sgd"], "compare_scratch_vs_pretrained.png", "Scratch vs Pretrained")
plot_compare(["2_pretrained_sgd", "3_adam", "4_rmsprop"], "compare_optimizers.png", "SGD vs Adam vs RMSProp")
plot_compare(["2_pretrained_sgd", "5_cosine_lr"], "compare_lr_fixed_vs_cosine.png", "LR fixed vs Cosine")
plot_compare(["2_pretrained_sgd", "6_batch32"], "compare_batch16_vs_32.png", "Batch 16 vs 32")
plot_compare(["2_pretrained_sgd", "7_no_weight_decay"], "compare_weight_decay.png", "Weight decay (L2) vs none")
plot_compare(["5_cosine_lr", "8_cosine_more_data"], "compare_more_data.png", "Original data vs + Kaggle images")
plot_compare(["4_rmsprop", "9_rmsprop_low_lr"], "compare_rmsprop_lr.png", "RMSProp lr 0.001 vs 0.0001")
plot_compare(SEED_RUNS, "compare_seeds.png", "Same settings, 3 seeds")
all_names = []
for e in EXPERIMENTS:
    all_names.append(e["name"])
plot_compare(all_names, "compare_all.png", "All experiments")

# ตารางสรุปแบบอ่านง่าย (เอาไปวางในรายงานได้)
with open(os.path.join(RESULT_DIR, "summary.md"), "w", encoding="utf-8") as f:
    f.write("| การทดลอง | เริ่มจาก | Optimizer | LR | Batch | Weight decay | Epoch | Val mAP50 | Test Precision | Test Recall | Test F1 | Test mAP50 |\n")
    f.write("|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    for r in summary:
        f.write("| " + " | ".join([str(r["name"]), str(r["start_from"]), str(r["optimizer"]),
                                    str(r["lr0"]) + " " + str(r["lr_schedule"]), str(r["batch"]), str(r["weight_decay"]),
                                    str(r["epochs_run"]), str(r["val_mAP50"]), str(r["test_precision"]),
                                    str(r["test_recall"]), str(r["test_f1"]), str(r["test_mAP50"])]) + " |\n")

print("\nเสร็จทั้งหมด โมเดลที่เลือก:", best_name, "| ดูผลใน", RESULT_DIR)
