# หน้าเว็บหลัก รันด้วย  streamlit run app.py
# ฟังก์ชันจัดการรูปอยู่ใน utils.py / หน้าตาเว็บอยู่ใน style.css

import os
import json
import numpy as np
import streamlit as st
from PIL import Image

from utils import fix_image, prepare_image, array_to_image, color_mean, to_base64, svg_img, IMG_SIZE, HAR_255

SIZE_TEXT = str(IMG_SIZE) + "×" + str(IMG_SIZE)   # ข้อความขนาดรูป เช่น 160×160 (ถ้าฟิวเปลี่ยน IMG_SIZE ข้อความบนเว็บเปลี่ยนตามเอง)


MAX_MB = 10             # กันคนอัปรูปใหญ่เกิน
MAX_PIXELS = 50000000   # กันรูปที่ไฟล์เล็กแต่จำนวนพิกเซลเยอะผิดปกติ (กินแรมจนเว็บค้าง) 50 ล้านพิกเซลพอสำหรับกล้องมือถือ
LOW_CONF = 60           # ความมั่นใจต่ำกว่านี้ (%) จะขึ้นเตือนให้ลองถ่ายใหม่ (ปรับได้)
folder = os.path.dirname(os.path.abspath(__file__))
HERO_FILE = os.path.join(folder, "static", "hero.jpg")   # รูปหัวเว็บ เอารูปจาก dataset มาวางชื่อนี้
MODEL_FILE = os.path.join(folder, "models", "best_model.keras")   # โมเดลที่ฟิวเทรน
CLASS_FILE = os.path.join(folder, "models", "class_info.json")    # รายชื่อ 28 คลาส เรียงตามลำดับที่โมเดลตอบ

# ชื่อผักผลไม้ภาษาไทย (ชื่อคลาสในโมเดลเป็นอังกฤษ เช่น Apple__Healthy)
THAI_NAMES = {
    "Apple": "แอปเปิล", "Banana": "กล้วย", "Bellpepper": "พริกหยวก", "Carrot": "แครอท",
    "Cucumber": "แตงกวา", "Grape": "องุ่น", "Guava": "ฝรั่ง", "Jujube": "พุทรา",
    "Mango": "มะม่วง", "Orange": "ส้ม", "Pomegranate": "ทับทิม", "Potato": "มันฝรั่ง",
    "Strawberry": "สตรอว์เบอร์รี", "Tomato": "มะเขือเทศ",
}


# ===== ไอคอนกับสติกเกอร์ วาดเองเป็น svg แล้วแปลงเป็น <img> =====
ICON_LEAF = svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 48 48" fill="none" stroke="#171717" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 40 C8 18 26 6 42 6 C42 26 30 40 8 40 Z"/><path d="M8 40 L28 20"/></svg>')
ICON_ARROW = svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#171717" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>')
# ติ๊กกับกากบาทวาดมือ ไว้ขีดลงช่องในแถบขั้นตอน (ตั้งใจให้ล้นช่องนิดๆ เหมือนติ๊กด้วยปากกา)
ICON_CHECK = svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4F6815" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5 9-10"/></svg>')
ICON_TICK = svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 32 32" fill="none" stroke="#4F6815" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 17 C8 19 10 22 12.5 27 C16 17 21 10 29 4"/></svg>')
ICON_TICK_RED = svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 32 32" fill="none" stroke="#A63A12" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 17 C8 19 10 22 12.5 27 C16 17 21 10 29 4"/></svg>')
ICON_CROSS = svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 32 32" fill="none" stroke="#A63A12" stroke-width="3" stroke-linecap="round"><path d="M8 7 C13 13 19 20 25 26"/><path d="M25 7 C19 13 13 20 7 26"/></svg>')
ICON_ALERT = svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 48 48" fill="none" stroke="#A63A12" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="17"/><path d="M24 15v11"/><path d="M24 32.5v.5"/></svg>')
ICON_CAMERA = svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 48 48" fill="none" stroke="#5E544B" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 16h8l4-6h12l4 6h8v24H6z"/><circle cx="24" cy="27" r="8"/></svg>')

STICKER_APPLE = svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="78" height="78" viewBox="0 0 48 48"><path d="M24 15 C16 8 4 12 6 26 C8 40 18 46 24 42 C30 46 40 40 42 26 C44 12 32 8 24 15 Z" fill="#FF66CF" stroke="#171717" stroke-width="2"/><path d="M24 15 C24 10 26 6 29 4" fill="none" stroke="#171717" stroke-width="2" stroke-linecap="round"/><path d="M27 9 C31 5 37 6 38 8 C35 12 30 12 27 9 Z" fill="#22C55E" stroke="#171717" stroke-width="2"/></svg>')
STICKER_LEAF = svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="66" height="66" viewBox="0 0 48 48"><path d="M8 40 C8 18 26 6 42 6 C42 26 30 40 8 40 Z" fill="#22C55E" stroke="#171717" stroke-width="2"/><path d="M8 40 L30 18" stroke="#171717" stroke-width="2" stroke-linecap="round"/></svg>')
STICKER_SPARK = svg_img('<svg xmlns="http://www.w3.org/2000/svg" width="54" height="54" viewBox="0 0 48 48"><path d="M24 3 L28.5 19.5 L45 24 L28.5 28.5 L24 45 L19.5 28.5 L3 24 L19.5 19.5 Z" fill="#3B82F6" stroke="#171717" stroke-width="2" stroke-linejoin="round"/></svg>')


# ห่อ html ด้วย lang="th" บอกเบราว์เซอร์กับโปรแกรมอ่านหน้าจอว่าข้อความในนี้เป็นภาษาไทย
def th(html):
    return '<div lang="th">' + html + '</div>'


# แปลงตัวเลขเป็นข้อความ % (ถ้าน้อยมากจนปัดแล้วเป็น 0.0 ให้เขียน <0.1% แทน จะได้ไม่ดูเหมือนเลขพัง)
def pct_text(x):
    if x < 0.05:
        return "<0.1%"
    return str(round(x, 1)) + "%"


# ฟังก์ชันทำป้ายตรวจคุณภาพ
# photo = รูป base64 (ถ้าไม่มีใส่ "") / kind, conf = ข้อความในช่อง / stamp = ตราปั๊ม
# fresh = "สด" หรือ "เน่า" จะติ๊กลงช่องนั้นให้ (ถ้าไม่ใส่ = ช่องว่างทั้งคู่)
# others = ข้อความอันดับรองลงมา (ถ้าไม่ใส่ = ไม่โชว์)
def tag_html(photo, kind, conf, stamp, fresh="", others=""):
    html = '<div class="tag-card">'
    html = html + '<div class="tag-hole"></div>'
    if stamp != "":
        if stamp == "เน่า":
            html = html + '<div class="stamp stamp-rotten">' + stamp + '</div>'
        elif stamp == "ตรวจซ้ำ":
            html = html + '<div class="stamp stamp-unsure">' + stamp + '</div>'
        else:
            html = html + '<div class="stamp">' + stamp + '</div>'
    html = html + '<div class="tag-title">ป้ายตรวจคุณภาพ</div>'
    if photo != "":
        html = html + '<img class="tag-photo" src="' + photo + '" alt="รูปที่โมเดลเห็น ถูกบีบเป็น ' + SIZE_TEXT + '">'
        html = html + '<div class="tag-photo-note">รูปที่โมเดลเห็น (บีบเป็น ' + SIZE_TEXT + ')</div>'
    html = html + '<div class="tag-row"><span class="tag-key">ชนิด</span><span class="tag-line">' + kind + '</span></div>'

    # ช่องสด / เน่า ติ๊กช่องที่โมเดลตอบ
    # ติ๊กเป็นรูป โปรแกรมอ่านหน้าจอมองไม่เห็น เลยเขียนข้อความซ่อนไว้ให้ (class sr-only คนเห็นไม่ได้ แต่โปรแกรมอ่านได้)
    box_fresh = '<span class="box"></span>'
    box_rotten = '<span class="box"></span>'
    if fresh == "สด":
        box_fresh = '<span class="box">' + ICON_TICK + '<span class="sr-only">ติ๊กแล้ว</span></span>'
    if fresh == "เน่า":
        box_rotten = '<span class="box">' + ICON_TICK_RED + '<span class="sr-only">ติ๊กแล้ว</span></span>'
    html = html + '<div class="tag-row"><span class="tag-key">สถานะ</span><span>' + box_fresh + 'สด &nbsp; ' + box_rotten + 'เน่า</span></div>'
    html = html + '<div class="tag-row"><span class="tag-key">ความมั่นใจ</span><span class="tag-line">' + conf + '</span></div>'
    if others != "":
        html = html + '<div class="tag-others">' + others + '</div>'
    html = html + '<div class="tag-foot">ตรวจโดย KhadSan AI</div>'
    html = html + '</div>'
    return html


# ฟังก์ชันทำ 1 ข้อในเช็กลิสต์ขั้นตอน (หน้าตาเหมือนช่องติ๊กในป้ายตรวจ)
# state = "done" เสร็จแล้ว / "wait" รออยู่ / "unsure" โมเดลไม่แน่ใจ / "error" รูปใช้ไม่ได้ / "" ยังไม่เริ่ม
def step_html(num, title, sub, state):
    html = '<div class="step'
    if state != "":
        html = html + ' step-' + state
    html = html + '"><div class="step-num">' + num + '</div><div>'
    html = html + '<div class="step-title">' + title + '</div><div class="step-sub">' + sub + '</div>'

    # ช่องติ๊ก + คำเขียนมือข้างๆ
    html = html + '<div class="mark"><span class="tick-box">'
    if state == "done":
        html = html + ICON_TICK
    if state == "error":
        html = html + ICON_CROSS
    html = html + '</span>'
    if state == "done":
        html = html + 'เสร็จแล้ว'
    if state == "wait":
        html = html + 'รอโมเดล'
    if state == "unsure":
        html = html + 'ไม่แน่ใจ ตรวจซ้ำ'
    if state == "error":
        html = html + 'ใช้รูปนี้ไม่ได้'
    html = html + '</div>'

    html = html + '</div></div>'
    return html


# โหลดโมเดลครั้งเดียวแล้วจำไว้ (ไม่งั้นทุกครั้งที่กดอะไร streamlit จะรันใหม่ทั้งไฟล์ แล้วโหลดโมเดลซ้ำ ช้ามาก)
@st.cache_resource
def load_model():
    import keras   # import ตรงนี้ เพราะ tensorflow โหลดนาน หน้าเว็บจะได้เปิดเร็ว
    # compile=False เพราะเราแค่ทำนาย ไม่ได้เทรนต่อ
    # (ฟิวเซฟจาก keras รุ่นใหม่กว่าเรา ส่วนตั้งค่าการเทรนอ่านไม่ได้ แต่ตัวโมเดลใช้ได้ปกติ)
    model = keras.models.load_model(MODEL_FILE, compile=False)
    with open(CLASS_FILE, encoding="utf-8") as f:
        class_names = json.load(f)["class_names"]
    return model, class_names


# ให้โมเดลทาย แล้วเอา 3 อันดับแรก
# คืนเป็น list เช่น [["Apple", "Healthy", 97.2], ["Pomegranate", "Healthy", 2.6], ...]
def predict(model, class_names, data):
    probs = model.predict(data, verbose=0)[0]   # ได้ความน่าจะเป็นของทั้ง 28 คลาส
    order = np.argsort(probs)[::-1]             # เรียงลำดับคลาสจากคะแนนมากไปน้อย
    top = []
    for i in order[:3]:
        name = class_names[i]                   # เช่น "Apple__Healthy"
        fruit = name.split("__")[0]
        status = name.split("__")[1]
        top.append([fruit, status, float(probs[i]) * 100])
    return top


st.set_page_config(page_title="KhadSan AI", page_icon="🍎", layout="wide")

# โหลด css มาแต่งหน้าเว็บ
with open(os.path.join(folder, "style.css"), encoding="utf-8") as f:
    st.html("<style>" + f.read() + "</style>")


# ===== แถบบน =====
nav = '<div class="nav">'
nav = nav + '<div class="brand">' + ICON_LEAF + 'KhadSan AI</div>'
nav = nav + '</div>'
st.html(th(nav))


# ===== หัวเว็บ =====
hero = '<div class="hero">'

# ซ้าย : ข้อความ
hero = hero + '<div class="hero-left">'
hero = hero + '<span class="caption">ถึงทีมคัดแยกสินค้า,</span>'
hero = hero + '<h1 class="display">ผักผลไม้ชิ้นนี้<br>ยังสดอยู่ไหม?</h1>'
hero = hero + '<div class="body">ไม่ต้องไล่ดูด้วยตาทีละชิ้นจนล้า ถ่ายรูปหรืออัปโหลดรูปมา แล้วให้โมเดล CNN ที่ทีมเรา fine-tune ช่วยบอกชนิด และบอกว่า<span class="marker">สดหรือเน่า</span> ก่อนของเสียจะหลุดไปถึงมือลูกค้า</div>'
hero = hero + '<a class="pill" href="#scan">เริ่มสแกน ' + ICON_ARROW + '</a>'
hero = hero + '</div>'

# ขวา : ป้ายตรวจคุณภาพ + สติกเกอร์ (ถ้ามีรูป hero.jpg จะโชว์รูปข้างหลังป้าย)
hero = hero + '<div class="hero-right">'
if os.path.exists(HERO_FILE):
    hero = hero + '<div class="hero-photo" style="background-image: url(app/static/hero.jpg);"></div>'
hero = hero + '<div class="hero-tag">' + tag_html("", "", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; %", "") + '</div>'
hero = hero + '<div class="sticker" style="top: 0px; right: 0px; transform: rotate(12deg);">' + STICKER_APPLE + '</div>'
hero = hero + '<div class="sticker" style="top: 300px; right: 6px; transform: rotate(-14deg);">' + STICKER_LEAF + '</div>'
hero = hero + '<div class="sticker" style="top: 20px; left: 40px; transform: rotate(8deg);">' + STICKER_SPARK + '</div>'
hero = hero + '</div>'

hero = hero + '</div>'
st.html(th(hero))


# ===== ส่วนสแกน =====
st.html(th('<h2 id="scan" class="section-title">สแกนผักผลไม้</h2><div class="section-sub"><span class="caption">ทีละชิ้นนะ ถ่ายให้ชัด พื้นหลังเรียบๆ แสงพอ</span></div>'))

# นับรอบการสแกน ใช้ตั้งชื่อ key ของช่องใส่รูป (กด "สแกนชิ้นต่อไป" = รอบใหม่ = ได้ช่องใส่รูปว่างๆ)
if "round" not in st.session_state:
    st.session_state["round"] = 0

# แถบขั้นตอน (จองที่ไว้ก่อน รู้ว่ามีรูปไหมแล้วค่อยเติม)
steps_box = st.empty()

# ซ้าย = ใส่รูป + ป้ายผลตรวจ / ขวา = กรอบสแกน + ข้อมูลที่ส่งเข้าโมเดล
# วางป้ายผลไว้ใต้ช่องใส่รูป ผลจะได้ขึ้นใกล้ๆ จุดที่กด ไม่ต้องเลื่อนหา (บนมือถือก็ขึ้นต่อจากช่องใส่รูปเลย)
left, right = st.columns(2, gap="large")

# ----- ซ้าย : การ์ดใส่รูป -----
with left:
    with st.container(key="card_input"):
        # เลือกว่าจะใช้รูปจากไหน (ไม่เปิดกล้องเองอัตโนมัติ เปิดเฉพาะตอนเลือก)
        mode = st.segmented_control("เลือกวิธีใส่รูป", [":material/upload: อัปโหลดรูป", ":material/photo_camera: ถ่ายรูป"],
                                    default=":material/upload: อัปโหลดรูป", required=True,
                                    key="mode", label_visibility="collapsed", width="stretch")

        # บอกก่อนใส่รูปเลยว่าโมเดลรู้จักอะไรบ้าง (ผักผลไม้อื่นโมเดลจะเดาเป็น 14 ชนิดนี้อยู่ดี)
        known = '<div class="known">โมเดลรู้จัก ' + str(len(THAI_NAMES)) + ' ชนิด: ' + ' · '.join(THAI_NAMES.values()) + '</div>'

        file = None
        if mode == ":material/upload: อัปโหลดรูป":
            st.html(th('<h3 class="card-title">อัปโหลดรูป</h3><div class="card-sub">กดปุ่ม "เลือกรูป" หรือลากรูปมาวางในกรอบประ<br>jpg / png ไม่เกิน ' + str(MAX_MB) + ' MB · สลับโหมดแล้วรูปเดิมจะหายนะ</div>' + known))
            file = st.file_uploader("เลือกไฟล์รูป", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="upload_" + str(st.session_state["round"]))
        else:
            st.html(th('<h3 class="card-title">ถ่ายรูปจากกล้อง</h3><div class="card-sub">ถ้ากล้องไม่ขึ้น ให้กดอนุญาตกล้องในเบราว์เซอร์ หรือสลับไปโหมดอัปโหลดแทน</div>' + known))
            file = st.camera_input("ถ่ายรูปผักผลไม้", label_visibility="collapsed", key="camera_" + str(st.session_state["round"]))

    # เปิดรูป + เช็กไฟล์ (รูปใหญ่ใช้เวลานิดนึง เลยขึ้นข้อความหมุนๆ ให้รู้ว่ากำลังทำอยู่)
    img = None
    error = ""
    if file is not None:
        with st.spinner("กำลังเตรียมรูป..."):
            if file.size > MAX_MB * 1024 * 1024:
                error = "ไฟล์ใหญ่เกิน " + str(MAX_MB) + " MB ลองใช้รูปที่เล็กลง"
            else:
                # ถ้าไฟล์เสียหรือไม่ใช่ jpg / png จริงจะเข้า except
                try:
                    img = Image.open(file, formats=["JPEG", "PNG"])
                    # เช็กจำนวนพิกเซลก่อน load (ตอน open ยังอ่านแค่หัวไฟล์ ยังไม่กินแรม)
                    if img.width * img.height > MAX_PIXELS:
                        img = None
                        error = "รูปนี้ความละเอียดสูงเกินไป ลองย่อรูปก่อนนะ"
                    else:
                        img.load()
                        img = fix_image(img)
                except Exception:
                    img = None
                    error = "เปิดรูปนี้ไม่ได้ ไฟล์อาจเสียหรือไม่ใช่ jpg / png จริง ลองรูปอื่นดูนะ"
        if error != "":
            st.error(error)

    # ----- ป้ายผลตรวจ : ให้โมเดลทาย แล้วกรอกลงป้าย -----
    predicted = False
    if img is not None:
        data = prepare_image(img)
        small = array_to_image(data)
        rgb = color_mean(data)

        # ทาย (ครั้งแรกต้องโหลดโมเดลก่อน อาจนานหน่อย) ถ้าโหลดไม่ได้ ป้ายจะกลับไปเป็นแบบรอโมเดล
        try:
            with st.spinner("AI กำลังตรวจ... (ครั้งแรกต้องโหลดโมเดล อาจนานหน่อย)"):
                model, class_names = load_model()
                top = predict(model, class_names, data)
            predicted = True
        except Exception:
            predicted = False

        result = '<div class="card">'
        result = result + '<h3 class="card-title">ผลตรวจ</h3>'
        if predicted:
            # อันดับ 1 = คำตอบหลัก
            fruit = top[0][0]
            status = top[0][1]
            conf = top[0][2]
            kind = THAI_NAMES.get(fruit, fruit) + ' (' + fruit + ')'
            if status == "Healthy":
                fresh = "สด"
            else:
                fresh = "เน่า"
            conf_text = str(round(conf, 1)) + " %"

            # อันดับ 2-3 ไว้ดูว่าโมเดลลังเลกับอะไร
            others = "รองลงมา: "
            for i in range(1, len(top)):
                if top[i][1] == "Healthy":
                    other_status = "สด"
                else:
                    other_status = "เน่า"
                if i > 1:
                    others = others + " · "
                others = others + THAI_NAMES.get(top[i][0], top[i][0]) + " " + other_status + " " + pct_text(top[i][2])

            # ความมั่นใจต่ำ = ไม่ปั๊มสด/เน่า ให้ปั๊มตรวจซ้ำแทน และไม่ติ๊กช่อง
            if conf < LOW_CONF:
                stamp = "ตรวจซ้ำ"
                tick = ""
                answer = "ไม่แน่ใจ"
            else:
                stamp = fresh
                tick = fresh
                answer = fresh

            result = result + '<div class="card-sub">ผลจาก AI ใช้ช่วยคัด ไม่ใช่คำตัดสินสุดท้าย</div>'
            result = result + '<div class="result-wrap"><div class="result-tag">' + tag_html(to_base64(small), kind, conf_text, stamp, tick, others) + '</div></div>'
            if conf < LOW_CONF:
                result = result + '<div class="tag-warn">ความมั่นใจต่ำ ลองถ่ายใหม่ให้เห็นชิ้นเดียวชัดๆ พื้นหลังเรียบ</div>'
            # ข้อความซ่อนไว้ให้โปรแกรมอ่านหน้าจออ่านผลออกเสียงทันทีที่ทายเสร็จ (role="alert")
            result = result + '<div class="sr-only" role="alert">ผลตรวจ: ' + THAI_NAMES.get(fruit, fruit) + ' ' + answer + ' ความมั่นใจ ' + str(round(conf, 1)) + ' เปอร์เซ็นต์</div>'
        else:
            result = result + '<div class="card-sub">ยังโหลดโมเดลไม่ได้ ป้ายนี้เลยยังว่างอยู่</div>'
            result = result + '<div class="result-wrap"><div class="result-tag">' + tag_html(to_base64(small), "--", "-- %", "รอโมเดล") + '</div></div>'
        result = result + '</div>'
        st.html(th(result))
        if predicted:
            # ปุ่มล้างรูปเดิม แล้วใส่ชิ้นต่อไปได้เลย ไม่ต้องเลื่อนขึ้นไปกดลบรูป
            if st.button("สแกนชิ้นต่อไป", key="next_item"):
                st.session_state["round"] = st.session_state["round"] + 1
                st.rerun()
        if predicted == False:
            st.warning("โหลดโมเดลไม่ได้: เช็กว่ามีไฟล์ models/best_model.keras กับ models/class_info.json และติดตั้ง tensorflow แล้ว")


# ----- ขวา : กรอบสแกน -----
with right:
    corners = '<div class="corner tl"></div><div class="corner tr"></div><div class="corner bl"></div><div class="corner br"></div>'

    box = '<div class="card">'
    box = box + '<h3 class="card-title">กรอบสแกน</h3>'
    if img is not None:
        box = box + '<div class="card-sub">รูปที่ใส่เข้ามา</div>'
        box = box + '<div class="frame has-img"><img class="frame-photo" src="' + to_base64(img) + '" alt="รูปผักผลไม้ที่ใส่เข้ามา">' + corners
        box = box + '<div class="scan-line"></div></div>'
        box = box + '<div class="status">' + ICON_CHECK + ' เตรียมรูปเสร็จแล้ว</div>'
    elif error != "":
        box = box + '<div class="card-sub">ใช้รูปนี้ไม่ได้</div>'
        box = box + '<div class="frame frame-error">' + corners
        # รายละเอียด error ขึ้นในกล่องใต้ช่องใส่รูปแล้ว ตรงนี้บอกสั้นๆ พอ
        box = box + '<div class="frame-msg">' + ICON_ALERT + '<span class="msg">ลองใส่รูปใหม่ · ดูสาเหตุใต้ช่องใส่รูป</span></div></div>'
    else:
        box = box + '<div class="card-sub">ยังไม่มีรูป</div>'
        box = box + '<div class="frame">' + corners
        box = box + '<div class="frame-msg">' + ICON_CAMERA + '<span class="caption">ใส่รูปผักผลไม้ก่อนนะ</span></div></div>'
    box = box + '</div>'
    st.html(th(box))

    # ----- ข้อมูลที่ส่งเข้าโมเดล (ไว้โชว์อาจารย์ว่าเตรียมรูปจริง) -----
    if img is not None:
        names = ["R สีแดง", "G สีเขียว", "B สีน้ำเงิน"]
        shape = data.shape

        card = '<div class="card">'
        card = card + '<h3 class="card-title">ข้อมูลที่ส่งเข้าโมเดล</h3>'
        if HAR_255 == True:
            card = card + '<div class="card-sub">ค่าสีเฉลี่ย หลังบีบรูปเป็นจัตุรัส ' + str(shape[1]) + '×' + str(shape[2]) + ' และปรับเป็น 0–1</div>'
        else:
            card = card + '<div class="card-sub">ค่าสีเฉลี่ย (0–255) หลังบีบรูปเป็นจัตุรัส ' + str(shape[1]) + '×' + str(shape[2]) + ' · โมเดลปรับค่าสีต่อเองข้างใน</div>'
        for i in range(3):
            # ตัวเลขโชว์ตามสเกลที่ส่งเข้าโมเดลจริง (0-1 หรือ 0-255) / ความยาวแถบใช้ 0-1 เสมอ
            if HAR_255 == True:
                value = str(round(rgb[i], 2))
            else:
                value = str(round(rgb[i] * 255))
            card = card + '<div class="bar-row">'
            card = card + '<div class="bar-head"><b>' + names[i] + '</b><span>' + value + '</span></div>'
            card = card + '<div class="bar-bg"><div class="bar-fill" style="width: ' + str(round(rgb[i] * 100)) + '%;"></div></div>'
            card = card + '</div>'
        card = card + '<span class="chip">ขนาด ' + str(shape) + '</span>'
        card = card + '<span class="chip">ช่วงค่า ' + str(round(float(data.min()), 3)) + ' – ' + str(round(float(data.max()), 3)) + '</span>'
        # อธิบายตัวเลขในป้ายเป็นภาษาคน
        card = card + '<div class="chip-note">ขนาด = ' + str(shape[0]) + ' รูป · ' + str(shape[1]) + '×' + str(shape[2]) + ' พิกเซล · ' + str(shape[3]) + ' สี (R G B)<br>ช่วงค่า = สีเข้มสุดถึงสว่างสุดในรูป</div>'
        card = card + '</div>'
        st.html(th(card))


# ===== เติมแถบขั้นตอน ตามว่ามีรูปแล้วหรือยัง =====
if img is not None:
    s1 = "done"
    s2 = "done"
    if predicted == False:
        s3 = "wait"
    elif conf < LOW_CONF:
        s3 = "unsure"
    else:
        s3 = "done"
elif error != "":
    s1 = "error"
    s2 = ""
    s3 = ""
else:
    s1 = ""
    s2 = ""
    s3 = ""
steps = '<div class="steps">'
steps = steps + step_html("1", "ใส่รูป", "อัปโหลดหรือถ่ายจากกล้อง", s1)
if HAR_255 == True:
    step2_sub = "บีบเป็น " + SIZE_TEXT + " และปรับค่าสีเป็น 0–1"
else:
    step2_sub = "บีบเป็น " + SIZE_TEXT + " แล้วส่งเข้าโมเดล"
steps = steps + step_html("2", "ปรับรูป", step2_sub, s2)
steps = steps + step_html("3", "AI ตรวจ", "บอกชนิด สด/เน่า และ % ความมั่นใจ", s3)
steps = steps + '</div>'
steps_box.html(th(steps))


# ===== แถบท้ายเว็บ =====
foot = '<div class="footer">'
foot = foot + '<div class="footer-brand">KhadSan AI</div>'
foot = foot + '<span class="caption">คัดของสด ก่อนของเน่าหลุดถึงมือลูกค้า</span>'
foot = foot + '<div class="footer-small">โปรเจกต์วิชา CS461 AI for Business Solutions · โมเดล MobileNetV2 ที่ทีม fine-tune ด้วย Fruit and Vegetable Diseases Dataset (Kaggle)</div>'
foot = foot + '</div>'
st.html(th(foot))


# ===== โหลดโมเดลรอไว้ก่อน =====
# วางไว้ท้ายสุด หน้าเว็บขึ้นครบแล้วค่อยโหลด ระหว่างคนอ่านหัวเว็บ โมเดลก็โหลดเสร็จพอดี
# คนแรกที่อัปรูปจะไม่ต้องรอโหลดโมเดลอีก (ถ้าโหลดไม่ได้ก็ข้ามไปก่อน ไว้ไปแจ้งตอนทาย)
try:
    load_model()
except Exception:
    pass
