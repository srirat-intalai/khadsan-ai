// JavaScript ของหน้าเว็บ KhadSan AI (ทีมเขียนเอง ไม่ได้ดึงจากที่อื่น)
// ทำ 4 อย่าง
//   1) เลือกรูปแล้ว โชว์รูปตัวอย่างให้ดูก่อนกดตรวจ (รูปยังไม่ถูกส่งไปไหน จนกว่าจะกดปุ่ม)
//   2) ไฟล์ใหญ่เกินกำหนด บอกเลยตั้งแต่ตอนเลือก ไม่ต้องรอส่ง
//   3) กดตรวจแล้ว ปุ่มเปลี่ยนเป็น "AI กำลังตรวจ…" และกดซ้ำไม่ได้
//   4) โหมดกล้อง : เปิดกล้อง (ได้ทั้งเว็บแคมบนคอม และกล้องหลังมือถือ) -> กดถ่าย -> รูปเข้าช่องเลือกรูปเหมือนอัปโหลด
// ถ้าเบราว์เซอร์ปิด JavaScript ไฟล์นี้จะไม่ทำงาน แต่เว็บยังส่งรูปได้ตามปกติ (แค่ไม่มีปุ่มเปิดกล้อง)

// หน้าเว็บมีฟอร์มใส่รูปแค่อันเดียว
var form = document.querySelector(".scan-form");
var input = form.querySelector('input[type="file"]');
var drop = form.querySelector(".drop");
var warn = form.querySelector(".drop-warn");
var button = form.querySelector(".scan-btn");
var maxMb = Number(form.getAttribute("data-max-mb"));
var preview = null;   // รูปตัวอย่าง สร้างตอนเลือกรูปครั้งแรก


// ----- 1) และ 2) ตอนเลือกรูป -----
input.addEventListener("change", function () {
    var file = input.files[0];
    warn.hidden = true;
    input.setCustomValidity("");   // ล้างข้อความเตือนเก่าออกก่อน

    // ไม่ได้เลือกรูป (กดยกเลิก)
    if (!file) {
        if (preview) {
            preview.hidden = true;
        }
        return;
    }

    // ไฟล์ใหญ่เกิน : ไม่ให้ส่ง และบอกเหตุผล (เซิร์ฟเวอร์ก็เช็กซ้ำอีกรอบอยู่แล้ว)
    if (file.size > maxMb * 1024 * 1024) {
        var text = "ไฟล์ใหญ่เกิน " + maxMb + " MB ลองใช้รูปที่เล็กลง";
        warn.textContent = text;
        warn.hidden = false;
        input.setCustomValidity(text);
        if (preview) {
            preview.hidden = true;
        }
        return;
    }

    // สร้างรูปตัวอย่างครั้งแรกครั้งเดียว ครั้งต่อไปใช้อันเดิม
    if (!preview) {
        preview = document.createElement("img");
        preview.className = "preview";
        preview.alt = "รูปที่เลือกไว้";
        // เบราว์เซอร์เปิดรูปนี้ไม่ได้ (เช่น ไฟล์ HEIC) ก็แค่ไม่โชว์ตัวอย่าง ยังส่งตรวจได้
        preview.addEventListener("error", function () {
            preview.hidden = true;
        });
        drop.appendChild(preview);
    }

    // ลบรูปตัวอย่างเก่าออกจากหน่วยความจำก่อน แล้วโชว์รูปใหม่
    if (preview.src) {
        URL.revokeObjectURL(preview.src);
    }
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
});


// ----- 3) ตอนกดตรวจ -----
form.addEventListener("submit", function (event) {
    // กดไปแล้วรอบหนึ่ง กดซ้ำไม่ส่งซ้ำ
    if (form.classList.contains("is-busy")) {
        event.preventDefault();
        return;
    }
    form.classList.add("is-busy");
    button.setAttribute("aria-disabled", "true");
    closeCamera();   // ส่งรูปแล้ว ปิดกล้องด้วย ไฟกล้องจะได้ดับ
});


// กดปุ่ม Back กลับมาหน้านี้ เบราว์เซอร์บางตัวจำหน้าเดิมไว้ทั้งหน้า ปุ่มจะค้างเป็น "กำลังตรวจ" เลยคืนค่าให้
window.addEventListener("pageshow", function () {
    form.classList.remove("is-busy");
    button.removeAttribute("aria-disabled");
});


// ----- 4) โหมดกล้อง -----
var camRow = form.querySelector(".cam-row");
var cam = form.querySelector(".cam");
var video = form.querySelector(".cam-video");
var camMsg = form.querySelector(".cam-msg");
var stream = null;   // ภาพจากกล้องที่เปิดอยู่ (null = ปิดอยู่)

// โชว์ปุ่ม "เปิดกล้อง" เฉพาะเบราว์เซอร์ที่เปิดกล้องได้
// (กล้องเปิดได้แค่เว็บที่เป็น https หรือ localhost เท่านั้น เป็นกฎของเบราว์เซอร์)
if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    camRow.hidden = false;
}

function showCamMsg(text) {
    camMsg.textContent = text;
    camMsg.hidden = false;
}

// ปิดกล้อง : หยุดทุกสัญญาณภาพ ไฟกล้องดับ แล้วกลับไปโชว์ปุ่มเปิดกล้อง
function closeCamera() {
    if (stream) {
        var tracks = stream.getTracks();
        for (var i = 0; i < tracks.length; i++) {
            tracks[i].stop();
        }
        stream = null;
    }
    video.srcObject = null;
    cam.hidden = true;
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        camRow.hidden = false;
    }
}

// กด "เปิดกล้อง"
form.querySelector(".cam-open").addEventListener("click", function () {
    camMsg.hidden = true;
    // facingMode environment = ขอกล้องหลังของมือถือ (บนคอมจะได้เว็บแคมตัวที่มี)
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false })
        .then(function (s) {
            stream = s;
            video.srcObject = s;
            video.play();
            camRow.hidden = true;
            cam.hidden = false;
        })
        .catch(function (err) {
            // บอกเหตุผลเป็นภาษาไทย แล้วให้ใช้ปุ่มเลือกรูปแทน
            if (err.name == "NotAllowedError") {
                showCamMsg("เบราว์เซอร์ยังไม่ให้ใช้กล้อง กดอนุญาตกล้อง หรือใช้ปุ่มเลือกรูปจากเครื่องแทน");
            } else if (err.name == "NotFoundError" || err.name == "OverconstrainedError") {
                showCamMsg("ไม่เจอกล้องในเครื่องนี้ ใช้ปุ่มเลือกรูปจากเครื่องแทนนะ");
            } else {
                showCamMsg("เปิดกล้องไม่ได้ (กล้องอาจถูกแอปอื่นใช้อยู่) ใช้ปุ่มเลือกรูปจากเครื่องแทนนะ");
            }
        });
});

// กด "ถ่าย" : เอาภาพตอนนั้นมาทำเป็นไฟล์ jpg แล้วใส่ลงช่องเลือกรูป เหมือนเลือกไฟล์เอง
form.querySelector(".cam-shot").addEventListener("click", function () {
    if (!stream || video.videoWidth == 0) {
        showCamMsg("กล้องยังไม่พร้อม รอสักครู่แล้วกดถ่ายใหม่");
        return;
    }
    var canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);

    canvas.toBlob(function (blob) {
        try {
            var file = new File([blob], "camera.jpg", { type: "image/jpeg" });
            var box = new DataTransfer();   // กล่องใส่ไฟล์ ใช้ยัดไฟล์เข้าช่องเลือกรูป
            box.items.add(file);
            input.files = box.files;
            input.dispatchEvent(new Event("change"));   // ให้โค้ดข้อ 1) ทำรูปตัวอย่างให้
            closeCamera();
        } catch (e) {
            showCamMsg("เบราว์เซอร์นี้ใส่รูปจากกล้องไม่ได้ ใช้ปุ่มเลือกรูปจากเครื่องแทนนะ");
        }
    }, "image/jpeg", 0.9);
});

// กด "ปิดกล้อง"
form.querySelector(".cam-close").addEventListener("click", function () {
    closeCamera();
});

// ถ้าเลือกรูปจากเครื่องตอนกล้องเปิดอยู่ ก็ปิดกล้องไปเลย
input.addEventListener("click", function () {
    closeCamera();
});
