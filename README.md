# KhadSan AI : ตรวจความสดผลไม้ด้วย AI

โครงงาน **ระบบตรวจระดับความสดและคัดเกรดผักผลไม้อัตโนมัติด้วยดีปเลิร์นนิง**
(Automated Fruit and Vegetable Quality and Freshness Classifier) วิชา CS461 AI for Business Solutions

ถ่ายรูปหรืออัปโหลดรูปผลไม้ (ในรูปมีได้หลายลูก) แล้วเว็บจะ

- **ตีกรอบผลไม้ทุกลูก** ในรูป พร้อมเลขกำกับ
- บอก **ชนิด** (รับ 5 ชนิด: แอปเปิล กล้วย ส้ม ทับทิม มะนาว) และ **สด หรือ เน่า** ทีละลูก พร้อม % ความมั่นใจ
- สรุปในป้ายตรวจคุณภาพว่า พบกี่ลูก สดกี่ลูก เน่ากี่ลูก
- ลูกที่โมเดลมั่นใจต่ำกว่า 60% ขึ้นว่า **ตรวจซ้ำ** (กรอบสีเทา) ให้คนดูซ้ำอีกที
- **สแกนสด** : เปิดกล้องแล้วเล็งค้างไว้ กรอบสด/เน่าจะขึ้นตามผลไม้บนภาพสดเลย (ราว 4-5 ภาพต่อวินาทีบนโน้ตบุ๊ก ขึ้นกับเครื่องและเน็ต)

> ใช้เพื่อการศึกษา เป็นตัวช่วยคัดแยกเบื้องต้น ไม่ได้ใช้รับรองคุณภาพหรือความปลอดภัยของอาหาร

**ปัญหาที่อยากแก้:** พนักงานคัดแยก/QC ในคลังสินค้าและซูเปอร์มาร์เก็ต ตรวจผลไม้สด/เน่าด้วยตาทีละลูก ทำนานแล้วล้า ตรวจพลาดได้
ระบบนี้ตรวจได้ทีละหลายลูกจากรูปเดียว เหมาะกับงานที่ผลไม้วางรวมกันในลังหรือบนสายพาน


## ทีมและหน้าที่

| ชื่อเล่น | ตำแหน่ง | หน้าที่ |
|---|---|---|
| ฟิว | ML Engineer | โมเดลและไปป์ไลน์การเทรน |
| หยก | MLOps & Frontend Developer | เว็บแอป, GitHub, ช่วยงานเทรนโมเดล |
| นีโอ | Data QA | ตรวจข้อมูล, ทดสอบเว็บ, ตัวเลขทางธุรกิจ |
| เมษา | Report | รายงาน (Word) |
| ใบหม่อน | Presentation | สไลด์นำเสนอ (Canva) |


## ระบบทำงานยังไง

```
กล้อง / อัปโหลดรูป
      │
      ▼
เว็บ Flask (web/app.py) ── เช็กไฟล์ (jpg/png ≤ 10 MB) ── หมุนรูปให้ตรง ── พื้นโปร่งใสเป็นขาว
      │
      ▼
โมเดล YOLOv8n (web/models/best_detect.pt) ── ตีกรอบ + บอกคลาส เช่น Orange_Bad
      │
      ▼
หน้าเว็บ : รูปตีกรอบ (เขียว = สด / อิฐ = เน่า / เทา = ตรวจซ้ำ) + รายการทีละลูก + ป้ายตรวจคุณภาพ
```

- โมเดล: **YOLOv8n** (Object Detection) ของ Ultralytics ทีมเทรน/fine-tune เองบน Google Colab
- 10 คลาส = 5 ชนิด × Good (สด) / Bad (เน่า)
- เว็บ: Python **Flask** + HTML/CSS + JavaScript ที่ทีมเขียนเอง (ปิด JS แล้วยังอัปโหลดรูปได้)


## ข้อมูลที่ใช้

**ชุดเทรน : Fruits Quality (Roboflow Universe)**
- มีกรอบรอบผลไม้แต่ละลูก + ป้าย Good / Bad
- เราเก็บไว้ 5 ชนิด ตัดฝรั่งและคลาสที่ป้ายแปลกออก เหลือ 2,320 รูป
- รูปที่หน้าตาเกือบเหมือนกัน (ถ่ายลูกเดิมหลายช็อต) จับไว้กลุ่มเดียวกัน แล้วแบ่ง train / val / test = 70 / 15 / 15
  เพื่อไม่ให้รูปคล้ายกันไปอยู่ทั้งใน train และ test (กัน data leakage คะแนน test จะได้ไม่ดูดีเกินจริง)

**ชุดทดสอบภายนอก : Fruit and Vegetable Diseases Dataset (Kaggle)**
- รูปจากแหล่งอื่นที่โมเดลไม่เคยเห็น ใช้สอบว่าโมเดลใช้กับรูปจริงนอกชุดเทรนได้ไหม
- มีแค่ แอปเปิล กล้วย ส้ม (ไม่มีกรอบ ใช้ชื่อโฟลเดอร์เป็นคำตอบ) คัดคลาสละ 100 รูป ข้ามรูปซ้ำ


## การทดลองปรับแต่งโมเดล (Model Tuning)

baseline = เริ่มจาก yolov8n ที่เทรนกับ COCO มาแล้ว, SGD, learning rate 0.01 คงที่, batch 16, weight decay 0.0005
แต่ละการทดลองเปลี่ยนทีละอย่างจาก baseline

| การทดลอง | สิ่งที่เปลี่ยน |
|---|---|
| 1_scratch_sgd | เทรนจากศูนย์ (ไม่ใช้โมเดลที่เทรนมาแล้ว) |
| 2_pretrained_sgd | baseline |
| 3_adam | Optimizer = Adam |
| 4_rmsprop | Optimizer = RMSProp |
| 5_cosine_lr | Learning rate ค่อยๆ ลดแบบ Cosine |
| 6_batch32 | Batch size 32 |
| 7_no_weight_decay | ไม่ใช้ L2 (weight decay) |

- ทุกการทดลองใช้ **Early Stopping** (หยุดถ้าคะแนน validation ไม่ดีขึ้น 10 รอบ) สูงสุด 60 รอบ รูป 640×640
- เลือกตัวที่ดีที่สุดจาก **mAP50 บน validation** แล้ววัดผลจริงบน **test** (Precision, Recall, F1, mAP50, Confusion Matrix) และชุดทดสอบภายนอก
- หมายเหตุ: Early Stopping ของ YOLO ดูคะแนน mAP ไม่ได้ดู Validation Loss ตรงๆ (แต่เก็บกราฟ Loss ไว้ดูด้วย)
  และ YOLO detect ไม่มี Dropout ให้ปรับ จึงใช้ L2 เป็นตัวทดลองด้าน Regularization แทน (BatchNorm มีอยู่ในโมเดลแล้ว)

**ผลลัพธ์** (วัดบน test set 344 รูป ที่โมเดลไม่เคยเห็นตอนเทรน · ตารางเต็มและกราฟอยู่ในโฟลเดอร์ `results/`)

| การทดลอง | Test Precision | Test Recall | Test F1 | Test mAP50 |
|---|---|---|---|---|
| 1_scratch_sgd | 0.882 | 0.855 | 0.868 | 0.925 |
| 2_pretrained_sgd | 0.897 | 0.920 | 0.908 | 0.949 |
| 3_adam | 0.894 | 0.938 | 0.916 | 0.954 |
| 4_rmsprop | 0.359 | 0.623 | 0.455 | 0.472 |
| **5_cosine_lr (ตัวที่ใช้ในเว็บ)** | **0.927** | **0.960** | **0.943** | **0.960** |
| 6_batch32 | 0.895 | 0.918 | 0.907 | 0.945 |
| 7_no_weight_decay | 0.879 | 0.916 | 0.897 | 0.932 |

- ตัวที่ดีที่สุด (5_cosine_lr) ได้ **F1 0.943** ผ่านเป้า F1 ≥ 0.85 ที่ตั้งไว้ใน Proposal
- เริ่มจากโมเดลที่เทรนมาแล้ว (pretrained) ดีกว่าเทรนจากศูนย์ / Learning rate แบบ Cosine ดีที่สุด
- RMSProp เทรนไม่เสถียร (loss พุ่งสูงมากตั้งแต่รอบแรก คะแนนแกว่งตลอด)
- แต่ละการทดลองรันครั้งเดียว ผลที่ต่างกันราว 1 จุด (เช่น Adam กับ SGD, batch 16 กับ 32) ถือว่าใกล้เคียงกัน
- รายคลาส: แย่สุดคือ ส้มเน่า (F1 0.875) บางลูกถูกทายเป็นส้มสด

**ทดสอบกับรูปจากแหล่งอื่น (Kaggle 600 รูป ที่โมเดลไม่เคยเห็น)** : ทายถูกทั้งชนิดและสด/เน่า 58.8% · ชนิดถูก 74.2% · สด/เน่าถูก 75.8%
- ต่ำกว่า test set มาก เพราะรูปจากแหล่งอื่นถ่ายคนละแบบ (พื้นขาว รูปสตูดิโอ) กับรูปที่ใช้เทรน
- กล้วยและส้มสดยังดี (82–87%) แต่ **ส้มเน่าแทบทายไม่ได้ (5%)** และแอปเปิลได้ราวครึ่งเดียว
- แปลว่าก่อนใช้งานจริง ต้องเพิ่มรูปเทรนที่หลากหลายกว่านี้ (ดูข้อจำกัดในรายงาน)

**รอบ 2 : เพิ่มรูปจาก Kaggle เข้าชุดเทรน** (กำลังทำ)
- เอารูป Kaggle 3,000 รูป (แอปเปิล กล้วย ส้ม ชนิดละสด/เน่า 500 รูป) ที่**ไม่ซ้ำกับชุดทดสอบภายนอก** มาเพิ่มในชุดเทรน
- รูป Kaggle ไม่มีกรอบ เลยให้โมเดลรอบแรกช่วยตีกรอบ แล้วใช้ชื่อโฟลเดอร์ Kaggle เป็นคำตอบ สด/เน่า
  เก็บเฉพาะกรอบที่โมเดลเห็นเป็นผลไม้ชนิดเดียวกับชื่อโฟลเดอร์ และกรอบต้องกินพื้นที่รูปพอ (สุ่มดูด้วยตาแล้ว กรอบถูกราว 95%)
- เทียบ `5_cosine_lr` (ข้อมูลเดิม) กับ `8_cosine_more_data` (ข้อมูลเดิม + Kaggle) ใช้ train/val/test ชุดเดียวกัน
- ผลจะใส่ตรงนี้หลังเทรนเสร็จ


## โครงสร้างไฟล์

```
train/
  prepare_data.py       เตรียมข้อมูล (ชุดเทรน + ชุดทดสอบภายนอก + ตีกรอบรูป Kaggle สำหรับรอบ 2)
  train_yolo.py         เทรน 8 การทดลอง + วัดผล + กราฟ/ตาราง
  train_colab.ipynb     โน้ตบุ๊กสำหรับ Google Colab (ดึงโค้ด 2 ไฟล์บนมารัน)
  datasets/             ที่วางข้อมูล (ไม่ขึ้น GitHub ไฟล์ใหญ่)
web/
  app.py                หน้าเว็บ Flask + เรียกโมเดล + วาดกรอบ
  templates/index.html  หน้าตาเว็บ
  static/style.css      สีและการจัดหน้า
  static/scan.js        กล้อง / สแกนสด / ดูรูปก่อนส่ง / ปุ่มกำลังตรวจ / กันกดซ้ำ
  static/hero.jpg       รูปหัวเว็บ
  models/               best_detect.pt + class_info.json (ได้จากการเทรน)
  requirements.txt      ไลบรารีของเว็บ (ล็อกเวอร์ชันไว้)
  Dockerfile            สูตรสร้างเซิร์ฟเวอร์บน Hugging Face Spaces
  README.md             ค่าตั้งของ Hugging Face Spaces
results/                กราฟ ตาราง ผลการทดลอง (ใส่รายงาน/สไลด์)
```

> ไฟล์ `app.py`, `utils.py`, `style.css`, `models/best_model.keras` ที่อยู่นอกโฟลเดอร์ `web/` เป็น**เว็บรุ่นแรก (Streamlit + MobileNetV2)**
> โมเดลรุ่นแรกเทรนโดยฟิว (โค้ดอยู่ที่ [fifacnw/project_cs461](https://github.com/fifacnw/project_cs461))
> เก็บไว้เป็นตัวสำรองจนกว่าเว็บ Flask จะขึ้นออนไลน์ แล้วจะลบออก


## วิธีเทรนโมเดล (Google Colab)

1. เปิด `train/train_colab.ipynb` ใน Google Colab
2. Runtime → Change runtime type → **T4 GPU**
3. เตรียม dataset อย่างใดอย่างหนึ่ง
   - ใส่ Roboflow API key ใน Colab Secrets ชื่อ `ROBOFLOW_API_KEY` (ห้ามพิมพ์ key ลงในโค้ด) หรือ
   - zip โฟลเดอร์ `train/datasets/fruits_quality` ตั้งชื่อ `FruitsQuality.zip` อัปโหลดไว้ใน Google Drive โฟลเดอร์ `KhadSan_detect`
4. (แนะนำ) zip `train/datasets/external_test` ตั้งชื่อ `ExternalTest.zip` อัปโหลดไว้ที่เดียวกัน
5. ตั้ง `ROUND = 1` ในข้อ 4 ของโน้ตบุ๊ก แล้ว Runtime → **Run all** ผลเก็บใน Drive โฟลเดอร์ `KhadSan_detect` (หลุดกลางทาง กด Run all ใหม่ จะทำต่อจากที่ค้าง)
6. เอา `models/best_detect.pt` กับ `models/class_info.json` มาวางใน `web/models/`

**รอบ 2 (เพิ่มรูป Kaggle)** ทำในเครื่องตัวเองก่อน (ต้องมีโฟลเดอร์ Kaggle ที่ `train/datasets/fruit_diseases_kaggle` และโมเดลรอบแรกใน `web/models/`)

```bash
cd train
python prepare_data.py                 # ทำชุดทดสอบภายนอก (datasets/external_test)
python prepare_data.py --make-boxes    # ตีกรอบรูป Kaggle (datasets/kaggle_boxes) ต้องลง ultralytics
```

แล้ว zip `datasets/external_test` เป็น `ExternalTest.zip` กับ `datasets/kaggle_boxes` เป็น `KaggleBoxes.zip`
อัปโหลดไว้ใน Drive โฟลเดอร์ `KhadSan_detect_v2` ตั้ง `ROUND = 2` ในโน้ตบุ๊ก แล้ว Run all


## วิธีเปิดเว็บในเครื่อง

ต้องมี **Python 3.12** และไฟล์โมเดลใน `web/models/`

**Mac**

```bash
git clone https://github.com/srirat-intalai/khadsan-ai.git
cd khadsan-ai/web
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/srirat-intalai/khadsan-ai.git
cd khadsan-ai\web
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

แล้วเปิด http://localhost:7860 ในเบราว์เซอร์

- กด **เปิดกล้อง** แล้วเลือก **สแกนสด** (กรอบขึ้นบนภาพสด) หรือ **ถ่าย** แล้วกด **ตรวจเลย** (ได้ผลละเอียดพร้อมเหตุผลทีละลูก)
- หรือ **เลือกรูปจากเครื่อง** แล้วกด **ตรวจเลย**
- กล้องเปิดได้เฉพาะเว็บที่เป็น HTTPS หรือ localhost (กฎของเบราว์เซอร์)
- ถ่ายให้เห็นผลไม้ทั้งลูก แสงพอ ผลไม้ชนิดอื่นนอก 5 ชนิด โมเดลอาจทายผิดได้


## เปิดให้คนอื่นใช้ผ่านอินเทอร์เน็ต (วันนำเสนอ)

รันเว็บบนโน้ตบุ๊ก แล้วใช้ Cloudflare Tunnel ทำลิงก์ https ให้มือถือคนอื่นเปิดได้ (ฟรี ไม่ต้องสมัคร ใช้กล้องมือถือได้)

```bash
brew install cloudflared                      # ลงครั้งเดียว (Mac)
cd web && source venv/bin/activate && python app.py           # หน้าต่าง Terminal ที่ 1
cloudflared tunnel --url http://localhost:7860                # หน้าต่าง Terminal ที่ 2 จะได้ลิงก์ https://....trycloudflare.com
```

- ลิงก์ใช้ได้เฉพาะตอนที่โน้ตบุ๊กเปิดและรัน 2 คำสั่งนี้อยู่ ปิด Terminal = ลิงก์หยุด (เปิดใหม่ได้ลิงก์ใหม่)
- ระหว่างเปิดลิงก์ ใครมีลิงก์ก็เข้าเว็บได้ ใช้เสร็จแล้วปิด
- `web/Dockerfile` เผื่อไว้สำหรับที่ลงแบบ Docker (เช่น Hugging Face Spaces ซึ่งตอนนี้ต้องใช้แพ็กเกจเสียเงิน) ทดสอบในเครื่องแล้วใช้ได้ แรมราว 430 MB


## การป้องกันในเว็บ

- รับเฉพาะไฟล์ jpg / png / webp จริง ขนาดไม่เกิน 10 MB และไม่เกิน 50 ล้านพิกเซล
- ไม่เก็บรูปของผู้ใช้ไว้ในเซิร์ฟเวอร์ (แปลงรูปเป็นข้อความแสดงในหน้าเว็บอย่างเดียว)
- ภาพจากกล้องไม่ถูกส่งไปไหน จนกว่าผู้ใช้จะกดตรวจ หรือกดสแกนสด (สแกนสดส่งภาพย่อไปตรวจทีละภาพ ไม่เก็บรูป)
- ไฟล์เสียหรือโมเดลพัง เว็บแจ้งเป็นภาษาไทย ไม่แสดงข้อความ error ดิบของระบบ
- ผลไม้ลูกเดียวกันที่โดนตีกรอบซ้อนกันหลายชนิด จะเหลือกรอบเดียว ตัวเลขนับไม่เกินจริง
- JavaScript ทีมเขียนเอง ไม่ได้ดึงจากเว็บอื่น


## เครดิตและลิขสิทธิ์

**ข้อมูล**
- Fruits Quality Dataset โดยผู้ใช้ Roboflow `alex-day-qzfwa` (project `fruits-quality-qtdtf` version 1)
  https://universe.roboflow.com/alex-day-qzfwa/fruits-quality-qtdtf : สัญญาอนุญาต **CC BY 4.0**
- Fruit and Vegetable Disease (Healthy vs Rotten) โดย `muhammad0subhan` บน Kaggle
  https://www.kaggle.com/datasets/muhammad0subhan/fruit-and-vegetable-disease-healthy-vs-rotten : ดูเงื่อนไขการใช้งานในหน้า Kaggle

**ซอฟต์แวร์**
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) ใช้สัญญาอนุญาต **AGPL-3.0**
  ถ้าเอาโปรแกรมที่ใช้ YOLOv8 ไปเปิดให้คนอื่นใช้ (รวมถึงเปิดเป็นเว็บ) ต้องเปิดเผยซอร์สโค้ดด้วย repo นี้จึงเปิดเป็นสาธารณะ
- Flask, Pillow, PyTorch ตามสัญญาอนุญาตของแต่ละโปรเจกต์

**หน้าตาเว็บ**
- ฟอนต์ Anuphan, Mitr, Mali จาก Google Fonts
- รูปหัวเว็บ (`web/static/hero.jpg`) จาก Canva
