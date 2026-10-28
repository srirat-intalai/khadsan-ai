// JavaScript ของหน้าเว็บ KhadSan AI (ทีมเขียนเอง ไม่ได้ดึงจากที่อื่น)
// ทำ 5 อย่าง
//   1) เลือกรูปแล้ว โชว์รูปตัวอย่างให้ดูก่อนกดตรวจ (รูปยังไม่ถูกส่งไปไหน จนกว่าจะกดปุ่ม)
//   2) ไฟล์ใหญ่เกินกำหนด บอกเลยตั้งแต่ตอนเลือก ไม่ต้องรอส่ง
//   3) กดตรวจแล้ว ปุ่ม + ขั้นตอน + กรอบสแกน บอกว่า "AI กำลังตรวจ…" และกดซ้ำไม่ได้
//   4) โหมดกล้อง : เปิดกล้อง (เว็บแคมบนคอม / กล้องหลังมือถือ) -> กดถ่าย -> รูปเข้าช่องเลือกรูปเหมือนอัปโหลด
//   5) ได้ผลแล้ว ติ๊กขั้นตอนทีละขั้น (~5 วิ) แล้วค่อยโชว์ผล ให้เห็นว่า AI ทำอะไรไปทีละขั้น
// ถ้าเบราว์เซอร์ปิด JavaScript ไฟล์นี้จะไม่ทำงาน แต่เว็บยังส่งรูปและเห็นผลได้ตามปกติ

var page = document.documentElement;
var live = document.getElementById("live");      // ข้อความให้โปรแกรมอ่านหน้าจออ่าน
var steps = document.querySelectorAll(".step");

// หน้าเว็บมีฟอร์มใส่รูปแค่อันเดียว
var form = document.querySelector(".scan-form");
var input = form.querySelector('input[type="file"]');
var drop = form.querySelector(".drop");
var warn = form.querySelector(".drop-warn");
var button = form.querySelector(".scan-btn");
var maxMb = Number(form.getAttribute("data-max-mb"));
var preview = null;   // รูปตัวอย่าง สร้างตอนเลือกรูปครั้งแรก

// กรอบสแกนตอนยังไม่มีผล (มีแค่หน้าเริ่มต้น) ถ้ามี จะเอารูปที่เลือกไปโชว์ในกรอบนี้แทน
var stage = document.querySelector(".frame-empty");
var stageSub = document.querySelector(".frame-sub");


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
        preview.alt = "รูปที่เลือกไว้";
        // เบราว์เซอร์เปิดรูปนี้ไม่ได้ (เช่น ไฟล์ HEIC) ก็แค่ไม่โชว์ตัวอย่าง ยังส่งตรวจได้
        preview.addEventListener("error", function () {
            preview.hidden = true;
        });
        if (stage) {
            // หน้าเริ่มต้น : โชว์ในกรอบสแกนใหญ่ด้านขวา (กรอบจะได้ไม่บอกว่า "ยังไม่มีรูป" ทั้งที่เลือกแล้ว)
            preview.className = "frame-photo";
            stage.insertBefore(preview, stage.firstChild);
            stage.classList.add("has-img");
        } else {
            // หน้าผลตรวจ : กรอบสแกนมีรูปผลอยู่แล้ว เลยโชว์รูปเล็กในช่องเลือกรูปแทน
            preview.className = "preview";
            drop.appendChild(preview);
        }
    }

    // ลบรูปตัวอย่างเก่าออกจากหน่วยความจำก่อน แล้วโชว์รูปใหม่
    if (preview.src) {
        URL.revokeObjectURL(preview.src);
    }
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
    if (stageSub) {
        stageSub.textContent = "รูปที่เลือก · กดตรวจได้เลย";
    }
});


// ----- 3) ตอนกดตรวจ -----
form.addEventListener("submit", function (event) {
    // กดไปแล้วรอบหนึ่ง กดซ้ำไม่ส่งซ้ำ
    if (form.classList.contains("is-busy")) {
        event.preventDefault();
        return;
    }
    form.classList.add("is-busy");
    page.classList.add("busy-page");          // มุมกรอบสแกนกะพริบ (ดูใน style.css)
    button.setAttribute("aria-disabled", "true");
    closeCamera();   // ส่งรูปแล้ว ปิดกล้องด้วย ไฟกล้องจะได้ดับ

    // ขั้นตอน : 1 เสร็จ (ส่งรูปแล้ว) / 2 กำลังทำ (รอเซิร์ฟเวอร์ตอบจริง)
    for (var i = 0; i < steps.length; i++) {
        steps[i].classList.remove("now");
    }
    if (steps.length == 3) {
        steps[1].classList.add("now");
    }
    live.textContent = "ส่งรูปแล้ว AI กำลังตรวจ รอสักครู่";
});


// กดปุ่ม Back กลับมาหน้านี้ เบราว์เซอร์บางตัวจำหน้าเดิมไว้ทั้งหน้า ปุ่มจะค้างเป็น "กำลังตรวจ" เลยคืนค่าให้
window.addEventListener("pageshow", function () {
    form.classList.remove("is-busy");
    page.classList.remove("busy-page");
    button.removeAttribute("aria-disabled");
    for (var i = 0; i < steps.length; i++) {
        steps[i].classList.remove("now");
    }
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
            // ถ่ายเสร็จ เลื่อนไปที่ปุ่มตรวจเลย ไม่ต้องเลื่อนหาเอง
            button.scrollIntoView({ block: "center", behavior: "smooth" });
            button.focus();
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


// ----- 5) ได้ผลแล้ว : ติ๊กขั้นตอนทีละขั้น แล้วค่อยโชว์ผล -----
// html มี class "play" (ใส่ไว้ใน index.html ตอนมีผลตรวจ) = ให้เล่น
// เวลาแต่ละขั้น (มิลลิวินาที) รวมกันประมาณ 5 วิ
var stepTimes = [800, 2000, 2200];
var stepIndex = 0;
var timer = null;
var skipRow = document.querySelector(".skip-row");

function nextStep() {
    // ขั้นก่อนหน้า : เลิกหมุน แล้วโชว์ติ๊ก
    if (stepIndex > 0) {
        steps[stepIndex - 1].classList.remove("now");
        steps[stepIndex - 1].classList.add("shown");
    }
    // ยังมีขั้นต่อไป : ให้หมุน แล้วรอเวลาของขั้นนั้น
    if (stepIndex < steps.length) {
        steps[stepIndex].classList.add("now");
        timer = setTimeout(nextStep, stepTimes[stepIndex]);
        stepIndex = stepIndex + 1;
    } else {
        showResult();
    }
}

// โชว์ผลทั้งหมด (เรียกตอนเล่นจบ หรือกด "ดูผลทันที")
function showResult() {
    clearTimeout(timer);
    for (var i = 0; i < steps.length; i++) {
        steps[i].classList.remove("now");
        steps[i].classList.add("shown");
    }
    page.classList.remove("play");
    if (skipRow) {
        skipRow.hidden = true;
    }
    var summaryText = document.getElementById("summary-text");
    if (summaryText) {
        live.textContent = summaryText.textContent;
    }
}

if (page.classList.contains("play")) {
    if (skipRow) {
        skipRow.hidden = false;
        skipRow.querySelector(".skip-anim").addEventListener("click", showResult);
    }
    nextStep();
}
