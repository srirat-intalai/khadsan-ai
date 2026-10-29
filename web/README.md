---
title: KhadSan AI
emoji: 🍎
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
license: agpl-3.0
---

# KhadSan AI : ตรวจความสดผลไม้ด้วย AI

เว็บของโครงงานวิชา CS461 AI for Business Solutions
ถ่ายรูปหรืออัปโหลดรูปผลไม้ (แอปเปิล กล้วย ส้ม ทับทิม มะนาว) แล้ว AI จะตีกรอบทุกลูก บอกว่าสดหรือเน่า และลูกไหนต้องคัดออก

- โมเดล : YOLOv8n ที่ทีมเทรนเอง (Fruits Quality Dataset, Roboflow, CC BY 4.0)
- โค้ดทั้งหมดและรายละเอียดการทดลอง : https://github.com/srirat-intalai/khadsan-ai
- ใช้เพื่อการศึกษา เป็นตัวช่วยคัดแยกเบื้องต้น ไม่ได้ใช้รับรองคุณภาพอาหาร

ไฟล์ส่วนบน (ระหว่างเส้น ---) เป็นค่าตั้งของ Hugging Face Spaces : ใช้ Docker และเปิดเว็บที่ port 7860
