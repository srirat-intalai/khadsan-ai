# เว็บ KhadSan AI (Flask) ตีกรอบผลไม้ทุกลูกในรูป แล้วบอกว่าสดหรือเน่า
# รันในเครื่อง:  python app.py  แล้วเปิด http://localhost:7860
# หน้าตาเว็บอยู่ใน templates/index.html กับ static/style.css
# โมเดลอยู่ใน models/best_detect.pt (ได้จากการเทรนใน train/train_colab.ipynb)

import os
import io
import json
import base64
from flask import Flask, render_template, request, jsonify
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageStat


folder = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(folder, "models", "best_detect.pt")
CLASS_FILE = os.path.join(folder, "models", "class_info.json")

MAX_MB = 10             # กันคนอัปรูปใหญ่เกิน
MAX_PIXELS = 50000000   # กันรูปที่ไฟล์เล็กแต่พิกเซลเยอะผิดปกติ (กินแรมจนเว็บค้าง)
CONF_MIN = 0.25         # กรอบที่โมเดลมั่นใจต่ำกว่านี้ ไม่นับว่าเจอผลไม้
LOW_CONF = 60           # ความมั่นใจต่ำกว่านี้ (%) ให้ขึ้น "ตรวจซ้ำ"
HIGH_CONF = 85          # ความมั่นใจตั้งแต่นี้ขึ้นไป (%) ถือว่ามั่นใจสูง
MAX_FRUITS = 30         # โชว์รายการไม่เกินกี่ลูก (รูปที่มีผลไม้เยอะมาก หน้าเว็บจะได้ไม่ยาวเกิน)
SAME_FRUIT = 0.5        # กรอบ 2 กรอบทับกันเกินครึ่ง = ผลไม้ลูกเดียวกัน เก็บไว้แค่กรอบที่มั่นใจกว่า

# ชื่อไทยของผลไม้ 5 ชนิด (ชื่อคลาสในโมเดลเป็นอังกฤษ เช่น Apple_Good / Apple_Bad)
THAI_NAMES = {
    "Apple": "แอปเปิล", "Banana": "กล้วย", "Orange": "ส้ม",
    "Pomegranate": "ทับทิม", "Lime": "มะนาว",
}

# ขนาดรูปที่โมเดลใช้ตอนเทรน (อ่านจาก class_info.json ถ้าไม่มีใช้ 640)
IMG_SIZE = 640
if os.path.exists(CLASS_FILE):
    with open(CLASS_FILE, encoding="utf-8") as f:
        IMG_SIZE = json.load(f).get("img_size", 640)

# สีกรอบในรูป (สีเดียวกับเว็บ)
COLOR_GOOD = (79, 104, 21)      # เขียวมะกอก = สด
COLOR_BAD = (166, 58, 18)       # สีอิฐ = เน่า
COLOR_UNSURE = (94, 84, 75)     # หมึกจาง = ไม่แน่ใจ
COLOR_PAPER = (253, 251, 249)   # สีครีม ใช้ทำขอบรอบกรอบ กับสีตัวเลข


# ===== ไอคอน วาดเองเป็น svg แล้วแปลงเป็น <img> (แบบเดียวกับเว็บเดิม) =====
def svg_img(svg):
    text = base64.b64encode(svg.encode("utf-8")).decode()
    return '<img src="data:image/svg+xml;base64,' + text + '" alt="">'


ICONS = {
    "leaf": svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 48 48" fill="none" stroke="#171717" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 40 C8 18 26 6 42 6 C42 26 30 40 8 40 Z"/><path d="M8 40 L28 20"/></svg>'),
    "arrow": svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#171717" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'),
    "check": svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4F6815" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5 9-10"/></svg>'),
    "tick": svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 32 32" fill="none" stroke="#4F6815" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 17 C8 19 10 22 12.5 27 C16 17 21 10 29 4"/></svg>'),
    "cross": svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 32 32" fill="none" stroke="#A63A12" stroke-width="3" stroke-linecap="round"><path d="M8 7 C13 13 19 20 25 26"/><path d="M25 7 C19 13 13 20 7 26"/></svg>'),
    "alert": svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 48 48" fill="none" stroke="#A63A12" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="17"/><path d="M24 15v11"/><path d="M24 32.5v.5"/></svg>'),
    "camera": svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 48 48" fill="none" stroke="#5E544B" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 16h8l4-6h12l4 6h8v24H6z"/><circle cx="24" cy="27" r="8"/></svg>'),
    "apple": svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="78" height="78" viewBox="0 0 48 48"><path d="M24 15 C16 8 4 12 6 26 C8 40 18 46 24 42 C30 46 40 40 42 26 C44 12 32 8 24 15 Z" fill="#FF66CF" stroke="#171717" stroke-width="2"/><path d="M24 15 C24 10 26 6 29 4" fill="none" stroke="#171717" stroke-width="2" stroke-linecap="round"/><path d="M27 9 C31 5 37 6 38 8 C35 12 30 12 27 9 Z" fill="#22C55E" stroke="#171717" stroke-width="2"/></svg>'),
    "sticker_leaf": svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="66" height="66" viewBox="0 0 48 48"><path d="M8 40 C8 18 26 6 42 6 C42 26 30 40 8 40 Z" fill="#22C55E" stroke="#171717" stroke-width="2"/><path d="M8 40 L30 18" stroke="#171717" stroke-width="2" stroke-linecap="round"/></svg>'),
    "spark": svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="54" height="54" viewBox="0 0 48 48"><path d="M24 3 L28.5 19.5 L45 24 L28.5 28.5 L24 45 L19.5 28.5 L3 24 L19.5 19.5 Z" fill="#3B82F6" stroke="#171717" stroke-width="2" stroke-linejoin="round"/></svg>'),
}


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024   # ไฟล์ใหญ่กว่านี้ Flask ตัดทิ้งเอง

# ค่าที่หน้าเว็บใช้ทุกครั้ง ตั้งไว้ทีเดียวตรงนี้ ไม่ต้องส่งซ้ำทุกหน้า
app.jinja_env.globals["icons"] = ICONS
app.jinja_env.globals["thai_names"] = list(THAI_NAMES.values())
app.jinja_env.globals["max_mb"] = MAX_MB
app.jinja_env.globals["img_size"] = IMG_SIZE
app.jinja_env.globals["model_ready"] = os.path.exists(MODEL_FILE)   # ใส่ไฟล์โมเดลทีหลัง ต้องเปิดเว็บใหม่


# ===== จัดการรูป =====
# แก้รูปให้พร้อมใช้ (เหมือน fix_image ในเว็บเดิม)
def fix_image(img):
    img = ImageOps.exif_transpose(img)   # รูปจากมือถือบางทีหมุนเอง หมุนกลับให้ตรง
    # png พื้นหลังโปร่งใส ถ้าแปลงตรงๆ พื้นจะดำ เลยวางบนพื้นขาวก่อน
    if "A" in img.mode or "transparency" in img.info:
        img = img.convert("RGBA")
        white = Image.new("RGB", img.size, "white")
        white.paste(img, mask=img)
        img = white
    return img.convert("RGB")


# แปลงรูปเป็นข้อความ base64 ใส่ใน <img> ได้เลย (ไม่ต้องเซฟรูปลงเครื่อง = ไม่เก็บรูปของผู้ใช้)
def to_base64(img, max_size=900):
    temp = img.copy()
    temp.thumbnail((max_size, max_size))
    buf = io.BytesIO()
    temp.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ค่าสีเฉลี่ย R G B (0-255) หลังย่อรูป ไว้โชว์ว่าส่งอะไรเข้าโมเดล
def color_mean(img):
    small = img.copy()
    small.thumbnail((IMG_SIZE, IMG_SIZE))   # YOLO ย่อด้านยาวเป็น IMG_SIZE โดยไม่บีบรูป
    result = []
    for band in small.split():              # แยกเป็น 3 ชั้น R G B
        pixels = list(band.getdata())
        result.append(round(sum(pixels) / len(pixels)))
    return result, small.size


# ===== โมเดล =====
# โหลดครั้งเดียวแล้วจำไว้ (โหลดทุกครั้งที่มีคนส่งรูปจะช้ามาก)
model = None


def load_model():
    global model
    if model is None:
        from ultralytics import YOLO   # import ตรงนี้ เพราะโหลดนาน หน้าเว็บจะได้เปิดเร็ว
        model = YOLO(MODEL_FILE)
    return model


# ให้โมเดลหาผลไม้ในรูป ได้เป็น list ของผลไม้แต่ละลูก เรียงจากซ้ายไปขวา
def detect(img):
    # agnostic_nms=True : ลูกเดียวกันโดนตีกรอบ 2 ชนิด (เช่น แอปเปิล กับ ทับทิม) ให้เหลือกรอบเดียว ตัวเลขนับจะไม่เกินจริง
    result = load_model().predict(img, imgsz=IMG_SIZE, conf=CONF_MIN, iou=SAME_FRUIT,
                                  agnostic_nms=True, max_det=100, verbose=False)[0]
    fruits = []
    for i in range(len(result.boxes)):
        name = result.names[int(result.boxes.cls[i])]   # เช่น "Apple_Good"
        fruit = name.split("_")[0]
        quality = name.split("_")[1]
        conf = float(result.boxes.conf[i]) * 100
        xyxy = result.boxes.xyxy[i]
        box = [float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])]
        if conf < LOW_CONF:
            state = "unsure"
        elif quality == "Good":
            state = "good"
        else:
            state = "bad"
        fruits.append({"fruit": fruit, "thai": THAI_NAMES.get(fruit, fruit), "quality": quality,
                       "conf": round(conf), "box": box, "state": state})   # % ปัดเป็นเลขกลม อ่านง่าย

    fruits.sort(key=left_side)
    for i in range(len(fruits)):
        fruits[i]["num"] = i + 1
    return fruits


# ใช้ตอนเรียงผลไม้ : ดูขอบซ้ายของกรอบ
def left_side(f):
    return f["box"][0]


# ใช้ตอนเรียงกรอบ : ขนาดพื้นที่ของกรอบ
def box_area(f):
    return (f["box"][2] - f["box"][0]) * (f["box"][3] - f["box"][1])


# สีกรอบตามสถานะ
def box_color(f):
    if f["state"] == "good":
        return COLOR_GOOD
    if f["state"] == "bad":
        return COLOR_BAD
    return COLOR_UNSURE


# วาดกรอบ + เลขลงบนรูป (เลขตรงกับรายการในหน้าเว็บ)
def draw_boxes(img, fruits):
    out = img.copy()
    draw = ImageDraw.Draw(out)
    line = max(5, round(max(out.size) / 120))       # รูปใหญ่ เส้นก็หนาขึ้น
    ring = max(2, line // 2)                        # ความหนาขอบครีมรอบนอก
    font_size = max(16, round(max(out.size) / 22))  # ใหญ่พอให้อ่านเลขออกบนจอมือถือ
    font = ImageFont.load_default(size=font_size)

    # วาดกรอบใหญ่ก่อน กรอบเล็กทีหลัง กรอบเล็กจะไม่โดนกรอบใหญ่ทับ
    order = sorted(fruits, key=box_area, reverse=True)

    # รอบที่ 1 : วาดกรอบทุกลูก (ขอบครีมรอบนอก + กรอบสีด้านใน จะเห็นชัดทุกพื้นหลัง เช่น กรอบเขียวบนสนามหญ้า)
    for f in order:
        x1, y1, x2, y2 = f["box"]
        draw.rectangle([x1 - ring, y1 - ring, x2 + ring, y2 + ring], outline=COLOR_PAPER, width=ring)
        draw.rectangle([x1, y1, x2, y2], outline=box_color(f), width=line)

    # รอบที่ 2 : วาดป้ายเลขทีหลังกรอบทั้งหมด เลขจะไม่โดนเส้นกรอบของลูกอื่นทับ
    for f in order:
        x1 = f["box"][0]
        y1 = f["box"][1]
        label = str(f["num"])
        w = draw.textlength(label, font=font)
        draw.rectangle([x1, y1, x1 + w + font_size * 0.6, y1 + font_size * 1.3], fill=box_color(f))
        draw.text((x1 + font_size * 0.3, y1 + font_size * 0.1), label, fill=COLOR_PAPER, font=font)
    return out


# พื้นที่ที่กรอบ 2 กรอบทับกัน
def overlap(a, b):
    w = min(a["box"][2], b["box"][2]) - max(a["box"][0], b["box"][0])
    h = min(a["box"][3], b["box"][3]) - max(a["box"][1], b["box"][1])
    if w <= 0 or h <= 0:
        return 0
    return w * h


# ทีละลูก : ตัดรูปเล็กไว้โชว์ + เขียนเหตุผลว่าทำไม AI ตอบแบบนี้
# เหตุผลใช้แค่ข้อมูลจริง ไม่แต่งเอง
#   1) สิ่งที่ AI ให้มา : ชนิด สด/เน่า และ % ความมั่นใจ
#   2) สิ่งที่วัดจากรูปได้จริง ที่อาจทำให้ AI มั่นใจน้อยลง : ลูกเล็ก ชิดขอบ ซ้อนกัน มืด
def add_details(img, fruits):
    width, height = img.size
    for f in fruits:
        x1 = int(f["box"][0])
        y1 = int(f["box"][1])
        # กันกรอบเล็กจนไม่มีพื้นที่ (กว้าง/สูง 0) ตัดรูปไม่ได้
        x2 = max(int(f["box"][2]), x1 + 1)
        y2 = max(int(f["box"][3]), y1 + 1)
        crop = img.crop([x1, y1, x2, y2])
        f["thumb"] = to_base64(crop, max_size=120)

        # ระดับความมั่นใจเป็นคำพูด
        if f["conf"] >= HIGH_CONF:
            f["level"] = "มั่นใจสูง"
        elif f["conf"] >= LOW_CONF:
            f["level"] = "มั่นใจพอใช้"
        else:
            f["level"] = "มั่นใจต่ำ"

        # เหตุผลหลัก
        if f["state"] == "good":
            f["reason"] = "สีและผิวคล้ายรูป" + f["thai"] + "สดที่ AI เคยเรียน"
        elif f["state"] == "bad":
            f["reason"] = "เจอลักษณะคล้ายรูป" + f["thai"] + "เน่าที่ AI เคยเรียน"
        else:
            if f["quality"] == "Good":
                lean = "สด"
            else:
                lean = "เน่า"
            f["reason"] = "AI เอนไปทาง" + lean + " แต่มั่นใจไม่ถึง " + str(LOW_CONF) + "% เลยให้คนดูซ้ำ"

        # สิ่งที่อาจทำให้ AI มั่นใจน้อยลง (บอกเฉพาะลูกที่ยังไม่มั่นใจสูง)
        notes = []
        if f["conf"] < HIGH_CONF:
            if box_area(f) < width * height * 0.015:
                notes.append("ลูกนี้เล็กในรูป เห็นรายละเอียดผิวน้อย")
            if x1 <= 2 or y1 <= 2 or x2 >= width - 2 or y2 >= height - 2:
                notes.append("อยู่ชิดขอบรูป อาจเห็นไม่ครบลูก")
            for other in fruits:
                if other is not f and overlap(f, other) > box_area(f) * 0.2:
                    notes.append("ซ้อนกับลูกอื่น")
                    break
            if ImageStat.Stat(crop.convert("L")).mean[0] < 60:
                notes.append("ส่วนนี้ของรูปค่อนข้างมืด")
        f["notes"] = notes


# นับว่า สด / เน่า / ตรวจซ้ำ อย่างละกี่ลูก + จดเลขลูกที่ต้องคัดออก / ต้องดูซ้ำ
def count_states(fruits):
    summary = {"total": len(fruits), "good": 0, "bad": 0, "unsure": 0, "bad_nums": [], "unsure_nums": []}
    for f in fruits:
        summary[f["state"]] = summary[f["state"]] + 1
        if f["state"] == "bad":
            summary["bad_nums"].append("#" + str(f["num"]))
        if f["state"] == "unsure":
            summary["unsure_nums"].append("#" + str(f["num"]))
    return summary


# ใช้ตอนเรียงรายการ : เน่า (ต้องคัดออก) ขึ้นก่อน แล้วตรวจซ้ำ แล้วสด  (เลขลูกยังเป็นเลขเดิมตามตำแหน่งในรูป)
def list_order(f):
    if f["state"] == "bad":
        return 0
    if f["state"] == "unsure":
        return 1
    return 2


# ===== หน้าเว็บ =====
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/", methods=["POST"])
def scan():
    file = request.files.get("photo")
    if file is None or file.filename == "":
        return render_template("index.html", error="ยังไม่ได้เลือกรูป เลือกรูปก่อนแล้วค่อยกดตรวจนะ")
    if not os.path.exists(MODEL_FILE):
        return render_template("index.html", error="ยังไม่มีไฟล์โมเดล (models/best_detect.pt) ทีมกำลังเทรนอยู่")

    # เปิดรูป + เช็กไฟล์ (ถ้าไฟล์เสียหรือไม่ใช่รูปจริงจะเข้า except)
    try:
        img = Image.open(file.stream, formats=["JPEG", "PNG", "WEBP"])
        # เช็กจำนวนพิกเซลก่อน load (ตอน open ยังอ่านแค่หัวไฟล์ ยังไม่กินแรม)
        if img.width * img.height > MAX_PIXELS:
            return render_template("index.html", error="รูปนี้ความละเอียดสูงเกินไป ลองย่อรูปก่อนนะ")
        img.load()
        img = fix_image(img)
    except Exception:
        return render_template("index.html", error="เปิดรูปนี้ไม่ได้ ไฟล์อาจเสียหรือไม่ใช่ jpg / png จริง ลองรูปอื่นดูนะ")

    # ให้โมเดลตรวจ (ถ้าพัง ไม่โชว์ error ดิบให้ผู้ใช้เห็น)
    try:
        fruits = detect(img)
    except Exception:
        return render_template("index.html", photo=to_base64(img), error="ตอนนี้ AI ตรวจไม่ได้ ลองใหม่อีกครั้งนะ")

    add_details(img, fruits)
    summary = count_states(fruits)
    photo = to_base64(draw_boxes(img, fruits), max_size=1200)
    rgb, small_size = color_mean(img)

    # รายการในหน้าเว็บ : ลูกเน่าขึ้นก่อน (sort แบบนี้ลำดับเดิมในกลุ่มเดียวกันไม่เปลี่ยน)
    fruits.sort(key=list_order)
    more = len(fruits) - MAX_FRUITS
    if more < 0:
        more = 0
    return render_template("index.html",
        photo=photo, fruits=fruits[:MAX_FRUITS], more=more, summary=summary,
        rgb=rgb, small_size=small_size, original_size=img.size,
        low_conf=LOW_CONF, high_conf=HIGH_CONF)


# ===== สแกนสด =====
# หน้าเว็บส่งภาพจากกล้องมาทีละภาพ (ย่อแล้ว) ตอบกลับเป็นตำแหน่งกรอบ + สด/เน่า ให้หน้าเว็บวาดทับภาพสดเอง
# ไม่เก็บรูป ไม่วาดรูปส่งกลับ ส่งแค่ตัวเลข จะได้เร็ว
@app.route("/live", methods=["POST"])
def live():
    file = request.files.get("frame")
    if file is None or not os.path.exists(MODEL_FILE):
        return jsonify({"ok": False, "boxes": []})
    try:
        img = Image.open(file.stream, formats=["JPEG"])
        if img.width * img.height > MAX_PIXELS:
            return jsonify({"ok": False, "boxes": []})
        img.load()
        img = img.convert("RGB")
        fruits = detect(img)
    except Exception:
        return jsonify({"ok": False, "boxes": []})

    # ตำแหน่งกรอบเป็นสัดส่วน 0-1 ของรูป หน้าเว็บจะคูณกับขนาดภาพบนจอเอง
    w, h = img.size
    boxes = []
    for f in fruits:
        boxes.append({"x1": f["box"][0] / w, "y1": f["box"][1] / h, "x2": f["box"][2] / w, "y2": f["box"][3] / h,
                      "thai": f["thai"], "state": f["state"], "conf": f["conf"]})
    summary = count_states(fruits)
    return jsonify({"ok": True, "boxes": boxes, "total": summary["total"],
                    "good": summary["good"], "bad": summary["bad"], "unsure": summary["unsure"]})


# ไฟล์ใหญ่เกิน MAX_MB
@app.errorhandler(413)
def too_large(e):
    return render_template("index.html", error="ไฟล์ใหญ่เกิน " + str(MAX_MB) + " MB ลองใช้รูปที่เล็กลง"), 413


if __name__ == "__main__":
    # โหลดโมเดลรอไว้ก่อน แล้วลองตรวจรูปว่าง 1 ครั้ง (รอบแรกของ YOLO ช้าเสมอ)
    # คนแรกที่ส่งรูปจะได้ไม่ต้องรอนาน ถ้ายังไม่มีไฟล์โมเดลก็ข้ามไป
    if os.path.exists(MODEL_FILE):
        try:
            load_model().predict(Image.new("RGB", (IMG_SIZE, IMG_SIZE), "white"), imgsz=IMG_SIZE, verbose=False)
        except Exception:
            pass

    # threaded=False : ตรวจทีละรูป มีคนส่งรูปพร้อมกัน 2 คน คนที่ 2 จะรอคิว โมเดลจะไม่ชนกัน
    # Hugging Face Spaces ใช้ port 7860
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)), debug=False, threaded=False)
