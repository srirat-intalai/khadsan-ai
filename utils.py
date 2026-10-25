# ไฟล์นี้เก็บฟังก์ชันเกี่ยวกับรูปภาพ
# app.py จะ import ไปใช้

import io
import base64
import numpy as np
from PIL import Image, ImageOps


IMG_SIZE = 160          # ขนาดรูปที่โมเดลต้องการ (ตอนนี้ฟิวเทรนที่ 160 ถ้าเทรนใหม่เป็น 224 แก้ตรงนี้ที่เดียว)
HAR_255 = False         # โมเดลของฟิวมี Rescaling อยู่ข้างในแล้ว (แปลงสีเป็น -1 ถึง 1 เอง) เลยต้องส่งค่าสีดิบ 0-255 ห้ามหาร 255 ซ้ำ


# แก้รูปให้พร้อมใช้ก่อน
def fix_image(img):
    # รูปจากมือถือบางทีมันหมุนเอง อันนี้ช่วยหมุนกลับให้ตรง
    img = ImageOps.exif_transpose(img)
    # png ไดคัทพื้นหลังโปร่งใส ถ้าแปลงตรงๆ พื้นจะกลายเป็นสีดำ เลยเอาไปแปะบนพื้นขาวก่อน
    if "A" in img.mode or "transparency" in img.info:
        img = img.convert("RGBA")
        white = Image.new("RGB", img.size, "white")
        white.paste(img, mask=img)
        img = white
    # บังคับเป็น RGB 3 ช่อง (รูปขาวดำมี 1 ช่อง)
    img = img.convert("RGB")
    return img


# ฟังก์ชันปรับรูปให้พร้อมเข้าโมเดล
# รับรูป PIL เข้ามา -> คืน numpy array ขนาด (1, IMG_SIZE, IMG_SIZE, 3)
# รูปที่ส่งเข้ามาต้องผ่าน fix_image แล้วนะ (app.py ทำไว้ตอนเปิดรูป)
def prepare_image(img):
    # ย่อขยายเป็นสี่เหลี่ยมจัตุรัส IMG_SIZE x IMG_SIZE
    img = img.resize((IMG_SIZE, IMG_SIZE))

    # แปลงเป็นตัวเลข
    x = np.array(img, dtype="float32")

    if HAR_255 == True:
        x = x / 255.0

    # เพิ่มมิติข้างหน้า เพราะโมเดลรับเป็นก้อน (batch) -> (1, IMG_SIZE, IMG_SIZE, 3)
    x = np.expand_dims(x, axis=0)

    return x


# แปลง array ที่เตรียมแล้ว กลับเป็นรูป เอาไว้โชว์บนเว็บ
def array_to_image(data):
    temp = data[0]
    if HAR_255 == True:
        temp = temp * 255
    return Image.fromarray(temp.astype("uint8"))


# หาค่าสีเฉลี่ย R G B ออกมาเป็นค่า 0-1
def color_mean(data):
    result = []
    for i in range(3):
        m = float(data[0, :, :, i].mean())
        if HAR_255 == False:
            m = m / 255
        result.append(m)
    return result


# แปลง svg ที่วาดเอง ให้เป็นแท็ก <img> (st.html ไม่ยอมโชว์ <svg> ตรงๆ)
# alt ว่างไว้ เพราะเป็นรูปตกแต่ง
def svg_img(svg):
    text = base64.b64encode(svg.encode("utf-8")).decode()
    return '<img src="data:image/svg+xml;base64,' + text + '" alt="">'


# แปลงรูปเป็นข้อความ base64 เพื่อเอาไปใส่ใน <img> ของ html
def to_base64(img, max_size=900):
    temp = img.copy()
    temp.thumbnail((max_size, max_size))   # ย่อรูปใหญ่ๆ ลงก่อน เว็บจะได้ไม่หน่วง
    buf = io.BytesIO()
    temp.save(buf, format="JPEG", quality=85)
    text = base64.b64encode(buf.getvalue()).decode()
    return "data:image/jpeg;base64," + text
