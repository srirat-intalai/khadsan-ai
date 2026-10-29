# สูตรสร้างเซิร์ฟเวอร์สำหรับ Hugging Face Spaces (แบบ Docker)
# เซิร์ฟเวอร์จะทำตามนี้ทีละบรรทัด : ลง Python -> ลงไลบรารี -> ก๊อปโค้ด -> เปิดเว็บ

FROM python:3.12-slim

# opencv (ultralytics ใช้) ต้องมีไลบรารีของระบบ 2 ตัวนี้
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face ให้รันด้วย user id 1000 (ไม่ใช่ root)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    YOLO_CONFIG_DIR=/home/user/.config/Ultralytics
WORKDIR $HOME/app

# ลง PyTorch แบบ CPU ก่อน (เซิร์ฟเวอร์ฟรีไม่มีการ์ดจอ รุ่น CPU ไฟล์เล็กกว่ารุ่นการ์ดจอมาก)
RUN pip install --no-cache-dir torch==2.15.0 torchvision==0.29.2 --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ก๊อปโค้ด หน้าเว็บ และโมเดล
COPY --chown=user . .

EXPOSE 7860
CMD ["python", "app.py"]
