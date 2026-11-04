# วิธีเทรนโมเดล และเทรนเพิ่มเมื่อมีรูปใหม่

เทรนบน Google Colab (ได้การ์ดจอฟรี) ไม่ต้องเทรนในเครื่องตัวเอง
โค้ดเทรนอยู่ในโฟลเดอร์ `train/`

| ไฟล์ | ทำอะไร |
|---|---|
| `prepare_data.py` | แบ่งรูปชุดหลักเป็น train / val / test (กันรูปคล้ายกันข้ามชุด) และทำชุดทดสอบภายนอก |
| `train_yolo.py` | เทรนทุกการทดลอง วัดผล วาดกราฟ ทำตาราง |
| `add_new_data.py` | เอารูปชุดใหม่ที่ตีกรอบเองมาแปลงเลขคลาสให้ตรงกับโมเดลเรา |
| `train_round1.ipynb` | โน้ตบุ๊ก Colab รอบ 1 : การทดลอง 1-7 |
| `train_round2.ipynb` | โน้ตบุ๊ก Colab รอบ 2 : เพิ่มรูปเข้าชุดเทรน (การทดลอง 8) และแก้ RMSProp (การทดลอง 9) |
| `train_round3.ipynb` | โน้ตบุ๊ก Colab รอบ 3 : เพิ่มส้มเน่า เทรนซ้ำ 3 seed (การทดลอง 10-12) และสอบข้อสอบใหม่ |
| `make_team_data.py` | รอบ 4 : แบ่งชุดรูปที่ทีมรวบรวมเพิ่ม เป็นรูปเทรน (ร่างกรอบด้วยโมเดล 11 แล้วคัดด้วยตา) กับข้อสอบ |
| `train_round4.ipynb` | โน้ตบุ๊ก Colab รอบ 4 : เพิ่มรูปมะนาว/ทับทิมของทีม เทรนซ้ำ 3 seed (การทดลอง 13-15) |


## 1. เทรนตามรอบเดิม (รอบ 1 / รอบ 2)

### ของที่ต้องเตรียมใน Google Drive

| รอบ | โฟลเดอร์ใน Drive (ต้องอยู่ใน My Drive ชั้นแรก) | ไฟล์ที่ต้องอัปโหลด |
|---|---|---|
| รอบ 1 | `KhadSan_detect` | `ExternalTest.zip` (ไม่บังคับ แต่ถ้าไม่มีจะไม่ได้ผลทดสอบกับรูปจากแหล่งอื่น) |
| รอบ 2 | `KhadSan_detect_v2` | `ExternalTest.zip` และ `KaggleBoxes.zip` (บังคับทั้งคู่) |
| รอบ 3 | `KhadSan_detect_v3` | `ExternalTest.zip`, `KaggleBoxes_v3.zip` และ `NewTest.zip` (บังคับทั้ง 3 ไฟล์ ดูข้อ 1.1) |
| รอบ 4 | `KhadSan_detect_v4` | `KaggleBoxes_v4.zip` และ `TeamTest.zip` (ส่วน `ExternalTest.zip`, `NewTest.zip` ใช้ของใน v3 ดูข้อ 1.2) |

ชุดรูปหลัก (Fruits Quality) เลือกได้ 1 ทาง
- ตั้ง Colab Secret ชื่อ `ROBOFLOW_API_KEY` (กดรูปกุญแจทางซ้ายใน Colab) ใส่ API key ของ Roboflow ห้ามพิมพ์ key ลงในโค้ด
- หรือ zip โฟลเดอร์ `train/datasets/fruits_quality` เป็น `FruitsQuality.zip` อัปโหลดไว้ในโฟลเดอร์ Drive ของรอบนั้น

ไฟล์ zip ขอได้จากหยก (เก็บไว้ในโฟลเดอร์ KhadSan_upload) หรือสร้างเองตามข้อ 4

### ขั้นตอน

1. ถ้าแก้โค้ดใน `train/` ต้อง push ขึ้น GitHub ก่อน เพราะโน้ตบุ๊กดึงโค้ดจาก GitHub
2. เปิด Colab : https://colab.research.google.com → File → Open notebook → แท็บ GitHub → พิมพ์ `srirat-intalai/khadsan-ai` → เลือกโน้ตบุ๊กของรอบนั้น
3. Runtime → Change runtime type → เลือก **T4 GPU** → Save
4. Runtime → **Run all** แล้วกดอนุญาตให้เข้า Google Drive
5. รอ รอบ 1 ราว 2-3 ชม. / รอบ 2 ราว 2.5-3 ชม. เปิดหน้าโน้ตบุ๊กทิ้งไว้ (ปิดแท็บนานๆ Colab อาจตัด)
6. หลุดกลางทาง : กด Run all ใหม่ได้เลย การทดลองที่เสร็จแล้วจะข้าม ทำต่อจากที่ค้าง

ทุกช่องในโน้ตบุ๊กมีตัวเช็ก ถ้าขาดไฟล์หรือโค้ดไม่ใช่รุ่นล่าสุด จะหยุดแล้วบอกว่าขาดอะไร

### เทรนเสร็จแล้วเอาไปใช้

ใน Drive จะได้
- `models/best_detect.pt` กับ `models/class_info.json` → เอาไปทับใน `web/models/` ของโปรเจกต์ แล้วเปิดเว็บใหม่
- `results/` → กราฟกับตาราง รอบ 1 วางใน `results/` / รอบ 2 วางใน `results/round2/`
- `runs/` ไม่ต้องโหลด (ไฟล์ใหญ่ เก็บใน Drive พอ)

ส่งลิงก์โน้ตบุ๊กที่รันเสร็จให้ทีมดูด้วย ดู 3 อย่างก่อนเลือกโมเดลใส่เว็บ
1. Test F1 ในตาราง (ช่อง "ดูผล")
2. ผลทดสอบกับรูปจากแหล่งอื่น (external)
3. รอบ 2 : ข้อ 8 ยังตีกรอบหน้าคนเป็นผลไม้อยู่ไหม

### 1.1 รอบ 3 ใช้ข้อมูลอะไร ทำไฟล์ zip ยังไง

รอบ 3 แก้จุดอ่อนของรอบ 2 : ส้มเน่าคะแนนตก / เทรนแบบละครั้งเดียว / ข้อสอบแหล่งอื่นมาจากที่เดียวกับรูปเทรนและไม่มีมะนาว ทับทิม

| ชุด (Roboflow, CC BY 4.0) | ใช้ทำอะไร | ชื่อคลาสเดิม → ของเรา |
|---|---|---|
| `trns-workspace-wydhc/rotten-orange-dvh3t` v5 | รูปเทรนเพิ่ม (ส้มเน่า 174 รูป) | rotten_orange → Orange_Bad, fresh_orange → Orange_Good |
| `sliit-b09eh/quality-detection-yy0x3` v1 | ข้อสอบใหม่ `new_test` (ทับทิมสด 150 รูป) | good → Pomegranate_Good |
| `yasmines-workspace-whz7y/lime-quality` v1 | ข้อสอบ `same_source_test` (มะนาว 298 รูป) | lime_bad → Lime_Bad, lime_good → Lime_Good |
| `curry/pomegranate-aws5r` v1 | ข้อสอบ `same_source_test` (ทับทิม 72 รูป) | 16 → Pomegranate_Good, 8 → Pomegranate_Bad (ดูจากรูป ชุดนี้ไม่ได้เขียนไว้) |

`same_source_test` มาจากชุดถ่ายเดียวกับ Fruits Quality (เจอรูปเดียวกันเป๊ะ) ตัดรูปที่ซ้ำออกแล้วแต่ยังไม่นับเป็นข้อสอบอิสระ
ชุดที่ดูแล้วไม่ใช้ : `lime-dataset-new` (ชื่อไฟล์ซ้ำกับ Fruits Quality 32 รูป) และชุดที่ไม่บอกสด/เน่า

สร้างไฟล์เอง (ในโฟลเดอร์ train ต้องมี `datasets/kaggle_boxes` กับ `datasets/external_test` จาก zip รอบ 2 และโหลด 4 ชุดข้างบนไว้ใน `datasets/roboflow/`)

```bash
cd khadsan-ai/train
P=../web/venv/bin/python
$P prepare_data.py                                   # ได้ datasets/data_5fruits (ชุดเดิม seed 42)
AV="datasets/data_5fruits,datasets/external_test,datasets/kaggle_boxes"
$P add_new_data.py --src datasets/roboflow/lime_quality --out datasets/same_source_test --rename "lime_bad=Lime_Bad,lime_good=Lime_Good" --per-class 150 --prefix lq_ --avoid "$AV"
$P add_new_data.py --src datasets/roboflow/pomegranate_aws5r --out datasets/same_source_test --rename "16=Pomegranate_Good,8=Pomegranate_Bad" --prefix pa_ --avoid "$AV"
$P add_new_data.py --src datasets/roboflow/quality_detection --out datasets/new_test --rename "good=Pomegranate_Good" --per-class 150 --prefix qd_ --avoid "$AV,datasets/same_source_test"
cp -R datasets/kaggle_boxes datasets/kaggle_boxes_v3
$P add_new_data.py --src datasets/roboflow/rotten_orange --out datasets/kaggle_boxes_v3 --rename "rotten_orange=Orange_Bad,fresh_orange=Orange_Good" --prefix ro_ --avoid "datasets/data_5fruits/val,datasets/data_5fruits/test,datasets/external_test,datasets/new_test,datasets/same_source_test"
cd datasets
zip -r -q KaggleBoxes_v3.zip kaggle_boxes_v3 -x "*.DS_Store"
zip -r -q NewTest.zip new_test same_source_test -x "*.DS_Store"
```

`--avoid` ข้ามรูปที่คล้ายรูปในโฟลเดอร์ที่ใส่ (กันข้อสอบรั่ว) / `--per-class` จำกัดจำนวนรูปต่อคลาส / Roboflow ทำรูปเดิมหลายเวอร์ชัน (หมุน กลับด้าน) สคริปต์เก็บไว้รูปเดียว

เทรน : อัปโหลด 3 ไฟล์ไว้ใน `KhadSan_detect_v3` แล้วเปิด `train_round3.ipynb` กด Run all (ราว 3-4 ชม.)
ผลที่ต้องดู : `results/new_tests.csv` (ข้อสอบใหม่ ทั้งโมเดลใหม่และโมเดล 5, 8) / `results/seed_summary.md` (3 seed แกว่งแค่ไหน) / `external_*_summary.txt`

### 1.2 รอบ 4 ใช้ข้อมูลอะไร

ชุดรูปที่ทีมรวบรวมเพิ่ม (Team-collected set) 444 รูป ไม่มีกรอบ มีแค่ชื่อโฟลเดอร์บอกคลาส
- มะนาวกับทับทิม (จุดอ่อนจากรอบ 3) สุ่มครึ่งหนึ่ง (seed 42) ไปเทรน อีกครึ่งเป็นข้อสอบ ผลไม้อื่นเป็นข้อสอบทั้งหมด → `team_collected_test` 287 รูป
- ครึ่งที่ไปเทรน : ให้โมเดล 11 ร่างกรอบ ชื่อคลาสใช้ตามโฟลเดอร์ แล้วเปิดดูทีละรูป
  ผ่าน 52 จาก 142 รูป (มะนาวเน่า 20 / มะนาวสด 3 / ทับทิมเน่า 23 / ทับทิมสด 6) ที่ไม่ผ่านจดไว้ใน `reject.txt`
  ส่วนใหญ่ที่ไม่ผ่านเป็นรูปกองผลไม้แน่นๆ ที่กรอบไม่ครบทุกลูก (ลูกที่ไม่มีกรอบจะสอนโมเดลผิดว่าไม่ใช่ผลไม้)

```bash
cd train
../web/venv/bin/python make_team_data.py --draft    # แบ่งชุด + ร่างกรอบ ดูรูปใน datasets/team_train_draft/preview
../web/venv/bin/python make_team_data.py --build    # รวมรูปที่ผ่านกับ kaggle_boxes_v3 ได้ datasets/kaggle_boxes_v4
cd datasets
zip -r -q KaggleBoxes_v4.zip kaggle_boxes_v4 -x "*.DS_Store"
zip -r -q TeamTest.zip team_collected_test -x "*.DS_Store"
```

เทรน : อัปโหลด 2 ไฟล์ไว้ใน `KhadSan_detect_v4` แล้วเปิด `train_round4.ipynb` กด Run all (ราว 3-4 ชม.)
ผลที่ต้องดู : `results/team_tests.csv` + `team_test_*_accuracy.csv` (รายคลาส) / `results/seed_summary_round4.md` / `new_tests.csv`
ก่อนเทรน โมเดล 11 ทำได้บน `team_collected_test` : ทายถูก 49.8% มะนาวเน่า 1/33 ทับทิมเน่า 2/49

### Colab ขึ้นว่าใช้ GPU ไม่ได้

แปลว่าโควตา GPU ฟรีของบัญชีนั้นหมด ต้องรอสักพักแล้วลองใหม่ หรือใช้บัญชี Google อื่น
ถ้าเปลี่ยนบัญชี ต้องสร้างโฟลเดอร์และอัปโหลดไฟล์ zip ไว้ใน Drive ของบัญชีนั้นใหม่ด้วย


## 2. เทรนเพิ่มเมื่อมีรูปใหม่

ใช้ได้กับรูปของผลไม้ 5 ชนิดเดิม (แอปเปิล กล้วย ส้ม ทับทิม มะนาว) สด/เน่า
รูปใหม่จะเข้าไปอยู่ในชุดเทรนอย่างเดียว ส่วน val กับ test ยังเป็นชุดเดิม คะแนนเลยเทียบกับรอบก่อนได้ตรงๆ

### ขั้นที่ 1 : ตีกรอบรูปใหม่ใน Roboflow

1. สมัคร https://roboflow.com (ฟรี) → Create New Project → เลือก **Object Detection**
2. อัปโหลดรูป แล้วลากกรอบรอบผลไม้ทุกลูก ทุกรูป
3. ตั้งชื่อคลาสให้สะกดตรงกับนี้เป๊ะ (ตัวใหญ่ตัวเล็ก ขีดล่าง ต้องตรง)
   `Apple_Bad` `Apple_Good` `Banana_Bad` `Banana_Good` `Lime_Bad` `Lime_Good` `Orange_Bad` `Orange_Good` `Pomegranate_Bad` `Pomegranate_Good`
   (Good = สด / Bad = เน่า ไม่ต้องมีครบทั้ง 10 ก็ได้)
4. Generate version แล้ว Export เลือก format **YOLOv8** → Download zip → แตก zip ไว้ในเครื่อง

ข้อควรระวัง
- อย่าเอารูปที่มีอยู่ในชุดทดสอบภายนอก (ExternalTest) หรือรูปจาก Fruits Quality มาใส่ซ้ำ ไม่งั้นคะแนนจะดูดีเกินจริง
- ถ่ายหลายแบบ หลายแสง หลายพื้นหลัง ช่วยมากกว่าถ่ายแบบเดิมเยอะๆ

### ขั้นที่ 2 : แปลงเลขคลาส แล้วรวมกับรูปเดิม

ใช้ venv ของเว็บได้เลย (มีไลบรารีครบแล้ว ถ้ายังไม่มีให้ทำ [run-web.md](run-web.md) ข้อ 2 ก่อน)

1. แตก `KaggleBoxes.zip` (ตัวที่ใช้เทรนรอบ 2) ไว้ที่ `train/datasets/kaggle_boxes` ให้ข้างในมีโฟลเดอร์ `images` กับ `labels`
2. รันคำสั่ง (เปลี่ยน `ที่อยู่โฟลเดอร์Roboflow` เป็นโฟลเดอร์ที่แตก zip จากขั้นที่ 1 ข้างในต้องมี `data.yaml`)

**Mac**

```bash
cd khadsan-ai/train
../web/venv/bin/python add_new_data.py --src "ที่อยู่โฟลเดอร์Roboflow" --out datasets/kaggle_boxes
```

**Windows (PowerShell)**

```powershell
cd khadsan-ai\train
..\web\venv\Scripts\python add_new_data.py --src "ที่อยู่โฟลเดอร์Roboflow" --out datasets\kaggle_boxes
```

ดูที่มันพิมพ์ออกมา
- ถ้ามีบรรทัด `!! ... ไม่ใช่ 1 ใน 10 คลาสของเรา` แปลว่าสะกดชื่อคลาสผิด กลับไปแก้ใน Roboflow แล้ว export ใหม่
- บรรทัดสุดท้าย จำนวนรูปกับไฟล์ป้ายต้องเท่ากัน
- รูปใหม่จะชื่อขึ้นต้นด้วย `new_` รูปเดิมในโฟลเดอร์ไม่หาย

3. zip โฟลเดอร์ใหม่เป็น `KaggleBoxes.zip`

**Mac** (ใช้คำสั่งนี้ ไม่ใช้คลิกขวา Compress เพราะจะมีโฟลเดอร์ขยะ `__MACOSX` ติดไป)

```bash
cd datasets
zip -r -q KaggleBoxes.zip kaggle_boxes -x "*.DS_Store"
```

**Windows (PowerShell)**

```powershell
cd datasets
Compress-Archive -Path kaggle_boxes -DestinationPath KaggleBoxes.zip
```

### ขั้นที่ 3 : เทรนบน Colab

1. ใน Drive สร้างโฟลเดอร์ใหม่ เช่น `KhadSan_detect_v3` แล้วอัปโหลด `KaggleBoxes.zip` (ตัวใหม่) กับ `ExternalTest.zip`
   ต้องเป็นโฟลเดอร์ใหม่ เพราะถ้าใช้โฟลเดอร์เดิม โน้ตบุ๊กจะเห็นว่าการทดลองเคยเสร็จแล้วและข้ามไป
2. เปิด `train_round2.ipynb` ใน Colab (ตามข้อ 1)
3. ในช่องของข้อ 4) แก้บรรทัด
   `OUT = "/content/drive/MyDrive/KhadSan_detect_v2"` เป็น `OUT = "/content/drive/MyDrive/KhadSan_detect_v3"`
   (แก้ใน Colab พอ ไม่ต้องแก้ใน GitHub)
4. Runtime → Run all
   - โน้ตบุ๊กจะพิมพ์ว่า "รูป Kaggle ที่ตีกรอบแล้ว ... รูป (ควรได้ 3000)" ตัวเลขจะเกิน 3000 เพราะรวมรูปใหม่แล้ว ไม่เป็นไร
5. ดูผล : เทียบ `8_cosine_more_data` (มีรูปใหม่) กับ `5_cosine_lr` (ไม่มีรูปใหม่) ทั้ง Test F1 และผลกับรูปจากแหล่งอื่น
   ถ้า 8 ดีกว่า ค่อยเอา `models/best_detect.pt` ไปใส่เว็บ (โน้ตบุ๊กเลือกตัวที่ Val mAP50 ดีสุดให้อยู่แล้ว เช็กชื่อใน `class_info.json`)

### อยากเพิ่มผลไม้ชนิดใหม่

ทำแบบข้างบนไม่ได้ เพราะโมเดลรู้จักแค่ 10 คลาสเดิม ต้องแก้หลายที่พร้อมกันแล้วเทรนใหม่ทั้งหมด
- `NEW_NAMES` ใน `prepare_data.py` และ `add_new_data.py` (เพิ่มชื่อคลาสต่อท้าย)
- `THAI_NAMES` ใน `web/app.py` (ชื่อภาษาไทยที่โชว์บนเว็บ)
- ชุดหลัก Fruits Quality ไม่มีผลไม้ชนิดใหม่ ต้องหารูปมาเองให้พอ (หลักร้อยรูปต่อคลาสขึ้นไป)
ควรคุยกับทีมก่อนทำ


## 3. ลองโค้ดเทรนในเครื่องก่อนขึ้น Colab (ไม่บังคับ)

ใช้ตอนแก้ `prepare_data.py` หรือ `train_yolo.py` แล้วอยากรู้ว่าโค้ดพังไหม ก่อนเสียเวลาเทรนจริงบน Colab

1. โหลด Fruits Quality จาก https://universe.roboflow.com/alex-day-qzfwa/fruits-quality-qtdtf (version 1 format YOLOv8)
   แตกไว้ที่ `train/datasets/fruits_quality` (ข้างในมี `data.yaml`, `train`, `valid`, `test`)
2. รัน (Mac ใช้ `../web/venv/bin/python` / Windows ใช้ `..\web\venv\Scripts\python`)

```bash
cd khadsan-ai/train
../web/venv/bin/python prepare_data.py
../web/venv/bin/python train_yolo.py --data datasets/data_5fruits/data.yaml --out test_run --only 2_pretrained_sgd --quick
```

`--quick` เทรนแค่ 1 รอบ ใช้รูป 10% ขนาดเล็ก ใช้เช็กว่าโค้ดไม่พัง (บนคอมไม่มีการ์ดจออาจใช้หลายนาที) คะแนนที่ได้ไม่มีความหมาย เสร็จแล้วลบโฟลเดอร์ `test_run` ทิ้งได้


## 4. สร้างไฟล์ zip เอง (ปกติไม่ต้องทำ ขอจากหยกได้)

ต้องมี
- รูป Kaggle ที่ `train/datasets/fruit_diseases_kaggle` (โหลดจาก https://www.kaggle.com/datasets/muhammad0subhan/fruit-and-vegetable-disease-healthy-vs-rotten)
- COCO128 ที่ `train/datasets/coco128` (https://github.com/ultralytics/assets/releases/download/v0.0.0/coco128.zip)
- โมเดลรอบแรกใน `web/models/`

```bash
cd khadsan-ai/train
../web/venv/bin/python prepare_data.py                 # ได้ datasets/external_test
../web/venv/bin/python prepare_data.py --make-boxes    # ได้ datasets/kaggle_boxes
```

แล้ว zip 2 โฟลเดอร์นั้นเป็น `ExternalTest.zip` กับ `KaggleBoxes.zip` แบบขั้นที่ 2 ข้อ 3
