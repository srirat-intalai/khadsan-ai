// JavaScript ของหน้าเว็บ KhadSan AI (ทีมเขียนเอง ไม่ได้ดึงจากที่อื่น)
// ทำ 6 อย่าง
//   1) เลือกรูปแล้ว โชว์รูปตัวอย่างให้ดูก่อนกดตรวจ (รูปยังไม่ถูกส่งไปไหน จนกว่าจะกดปุ่ม)
//   2) ไฟล์ใหญ่เกินกำหนด บอกเลยตั้งแต่ตอนเลือก ไม่ต้องรอส่ง
//   3) กดตรวจแล้ว ปุ่ม + ขั้นตอน + กรอบสแกน บอกว่า "AI กำลังตรวจ…" และกดซ้ำไม่ได้
//   4) โหมดกล้อง : เปิดกล้อง (เว็บแคมบนคอม / กล้องหลังมือถือ) -> กดถ่าย -> รูปเข้าช่องเลือกรูปเหมือนอัปโหลด
//   5) ได้ผลแล้ว ติ๊กขั้นตอนทีละขั้น แล้วค่อยโชว์ผล (ครั้งแรก ~5 วิ ครั้งต่อไปไม่ถึง 1 วิ)
//   6) สแกนสด : ส่งภาพจากกล้องไปตรวจทีละภาพ แล้ววาดกรอบทับภาพสด (ส่งภาพใหม่ก็ต่อเมื่อผลภาพเก่ากลับมาแล้ว เน็ตช้าก็ไม่ค้าง)
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
        // หน้าเริ่มต้น / หน้ารูปใช้ไม่ได้ : ขั้นที่ 1 เปลี่ยนเป็นติ๊ก "ส่งแล้ว"
        // จำของเดิมไว้ก่อน (ใส่ sent ไว้ จะได้รู้ว่า JS เปลี่ยนเอง) กด Back กลับมาจะคืนให้
        if (!steps[0].classList.contains("step-done")) {
            oldStepClass = steps[0].className;
            oldStepText = steps[0].querySelector(".mark-text").textContent;
            steps[0].className = "step step-done sent";
            steps[0].querySelector(".mark-text").textContent = "ส่งแล้ว";
        }
    }
    // ข้อความ "กดตรวจได้เลย" ในกรอบสแกน กดไปแล้ว เปลี่ยนเป็นกำลังตรวจ
    if (stageSub) {
        stageSub.textContent = "รูปที่เลือก · AI กำลังตรวจ…";
    }
    live.textContent = "ส่งรูปแล้ว AI กำลังตรวจ รอสักครู่";
});
var oldStepClass = "";
var oldStepText = "";


// กดปุ่ม Back กลับมาหน้านี้ เบราว์เซอร์บางตัวจำหน้าเดิมไว้ทั้งหน้า ปุ่มจะค้างเป็น "กำลังตรวจ" เลยคืนค่าให้
window.addEventListener("pageshow", function () {
    form.classList.remove("is-busy");
    page.classList.remove("busy-page");
    button.removeAttribute("aria-disabled");
    for (var i = 0; i < steps.length; i++) {
        steps[i].classList.remove("now");
    }
    // ติ๊ก "ส่งแล้ว" ที่ JS ใส่ไว้ตอนกดตรวจ คืนเป็นแบบเดิม
    if (steps.length == 3 && steps[0].classList.contains("sent")) {
        steps[0].className = oldStepClass;
        steps[0].querySelector(".mark-text").textContent = oldStepText;
    }
    if (stageSub && preview && !preview.hidden) {
        stageSub.textContent = "รูปที่เลือก · กดตรวจได้เลย";
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

// ปิดกล้อง : หยุดสแกนสด หยุดทุกสัญญาณภาพ ไฟกล้องดับ แล้วกลับไปโชว์ปุ่มเปิดกล้อง
function closeCamera() {
    stopLive();
    if (stream) {
        var tracks = stream.getTracks();
        for (var i = 0; i < tracks.length; i++) {
            tracks[i].stop();
        }
        stream = null;
    }
    video.srcObject = null;
    cam.hidden = true;
    camBack();
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
            camToFrame();
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

// จอคอม หน้าเริ่มต้น : ย้ายภาพกล้องไปไว้ในกรอบสแกนใหญ่ด้านขวา (กรอบจะได้ไม่บอกว่า "ใส่รูปผลไม้ก่อนนะ" ตอนกล้องเปิดอยู่)
// มือถือไม่ย้าย เพราะกรอบสแกนอยู่ล่างสุด ภาพกล้องจะห่างจากปุ่ม ถ่าย / สแกนสด แค่เปลี่ยนข้อความในกรอบ
var camStage = form.querySelector(".cam-stage");
var stageSubText = "";
var camMoved = false;
function camToFrame() {
    if (!stage) {
        return;
    }
    stageSubText = stageSub.textContent;
    if (window.matchMedia("(min-width: 701px)").matches) {
        stage.insertBefore(camStage, stage.firstChild);
        stage.classList.add("has-cam");
        stageSub.textContent = "ภาพจากกล้อง · กดถ่าย หรือสแกนสด ทางซ้าย";
    } else {
        // มือถือ : ภาพกล้องอยู่ด้านบนแล้ว ซ่อนการ์ดกรอบสแกนทั้งใบ ไม่ต้องเลื่อนผ่านการ์ดว่าง
        stage.parentNode.classList.add("cam-up");
    }
    camMoved = true;
}
// ปิดกล้องแล้ว ย้ายภาพกล้องกลับที่เดิม (ในฟอร์มด้านซ้าย) และคืนข้อความในกรอบ
function camBack() {
    if (!camMoved) {
        return;
    }
    if (stage.classList.contains("has-cam")) {
        cam.insertBefore(camStage, cam.firstChild);
    }
    stage.classList.remove("has-cam");
    stage.parentNode.classList.remove("cam-up");
    stageSub.textContent = stageSubText;
    camMoved = false;
}

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
        // ปิดกล้องก่อน (ภาพกล้องย้ายกลับที่เดิม) แล้วค่อยใส่รูปที่ถ่าย ข้อความในกรอบจะได้เป็นของรูปใหม่
        closeCamera();
        try {
            var file = new File([blob], "camera.jpg", { type: "image/jpeg" });
            var box = new DataTransfer();   // กล่องใส่ไฟล์ ใช้ยัดไฟล์เข้าช่องเลือกรูป
            box.items.add(file);
            input.files = box.files;
            input.dispatchEvent(new Event("change"));   // ให้โค้ดข้อ 1) ทำรูปตัวอย่างให้
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
// ครั้งแรกที่เปิดเว็บ เล่นช้าๆ รวมประมาณ 5 วิ ให้เห็นว่า AI ทำอะไรไปบ้าง
// ครั้งต่อไป ติ๊กเร็วๆ ไม่ถึง 1 วิ (AI ตรวจเสร็จจริงไม่ถึงวิ ไม่ต้องให้รอนาน)
var stepTimes = [800, 2000, 2200];
var seenBefore = false;
try {
    seenBefore = localStorage.getItem("khadsan-seen-steps") == "yes";
    localStorage.setItem("khadsan-seen-steps", "yes");
} catch (e) {
    // เบราว์เซอร์ไม่ให้จำ (เช่น โหมดไม่ระบุตัวตน) ก็เล่นแบบเต็มไป
}
if (seenBefore) {
    stepTimes = [200, 250, 250];
}
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


// ----- 6) สแกนสด -----
var liveUrl = form.getAttribute("data-live-url");
var liveBtn = form.querySelector(".cam-live");
var boxCanvas = form.querySelector(".cam-boxes");
var liveInfo = form.querySelector(".live-info");
var sendCanvas = document.createElement("canvas");   // ผืนไว้ย่อภาพก่อนส่ง (ไม่โชว์บนหน้าเว็บ)
var liveOn = false;
var liveTimer = null;

// สีกรอบ อ่านจากสีที่ตั้งไว้ใน style.css (สีเดียวกับกรอบในรูปผลตรวจ)
var cssColors = getComputedStyle(page);
var liveColors = {
    good: cssColors.getPropertyValue("--olive").trim(),
    bad: cssColors.getPropertyValue("--rotten").trim(),
    unsure: cssColors.getPropertyValue("--muted").trim()
};
var paperColor = cssColors.getPropertyValue("--paper").trim();
var liveWords = { good: "สด", bad: "เน่า", unsure: "ตรวจซ้ำ" };

liveBtn.addEventListener("click", function () {
    if (liveOn) {
        stopLive();
    } else {
        startLive();
    }
});

function startLive() {
    liveOn = true;
    liveBtn.textContent = "หยุดสแกน";
    liveBtn.setAttribute("aria-pressed", "true");
    liveInfo.textContent = "กำลังเริ่มสแกน…";
    liveInfo.classList.remove("live-bad");
    liveInfo.hidden = false;
    sendFrame();
}

function stopLive() {
    liveOn = false;
    clearTimeout(liveTimer);
    liveBtn.textContent = "สแกนสด";
    liveBtn.setAttribute("aria-pressed", "false");
    liveInfo.hidden = true;
    boxCanvas.getContext("2d").clearRect(0, 0, boxCanvas.width, boxCanvas.height);
}

// ส่งภาพ 1 ภาพไปตรวจ พอผลกลับมา ค่อยส่งภาพต่อไป
function sendFrame() {
    if (!liveOn) {
        return;
    }
    // กล้องยังไม่พร้อม หรือสลับไปแอปอื่นอยู่ รอแป๊บแล้วค่อยลองใหม่
    if (!stream || video.videoWidth == 0 || document.hidden) {
        liveTimer = setTimeout(sendFrame, 300);
        return;
    }
    // ย่อภาพให้ด้านยาวไม่เกิน 640 (ขนาดที่โมเดลใช้) ส่งเร็วขึ้น
    var scale = Math.min(1, 640 / Math.max(video.videoWidth, video.videoHeight));
    sendCanvas.width = Math.round(video.videoWidth * scale);
    sendCanvas.height = Math.round(video.videoHeight * scale);
    sendCanvas.getContext("2d").drawImage(video, 0, 0, sendCanvas.width, sendCanvas.height);

    sendCanvas.toBlob(function (blob) {
        var data = new FormData();
        data.append("frame", blob, "frame.jpg");
        fetch(liveUrl, { method: "POST", body: data })
            .then(function (res) {
                return res.json();
            })
            .then(function (result) {
                if (liveOn) {
                    drawLiveBoxes(result.boxes);
                    showLiveInfo(result);
                }
            })
            .catch(function () {
                if (liveOn) {
                    liveInfo.textContent = "เน็ตช้าหรือหลุด กำลังลองใหม่… (ใช้ปุ่ม ถ่าย แทนได้)";
                }
            })
            .then(function () {
                // ไม่ว่าผลจะมาหรือพัง ค่อยส่งภาพต่อไป (เว้นนิดนึง ไม่ให้เครื่องทำงานหนักเกิน)
                if (liveOn) {
                    liveTimer = setTimeout(sendFrame, 150);
                }
            });
    }, "image/jpeg", 0.7);
}

// วาดกรอบทับภาพสด
function drawLiveBoxes(boxes) {
    var w = video.clientWidth;
    var h = video.clientHeight;
    boxCanvas.width = w;
    boxCanvas.height = h;
    var ctx = boxCanvas.getContext("2d");
    ctx.clearRect(0, 0, w, h);

    // ภาพกล้องแสดงแบบไม่บีบ (อาจมีขอบว่างด้านข้าง) คำนวณว่าตัวภาพจริงอยู่ตรงไหนก่อน
    var s = Math.min(w / video.videoWidth, h / video.videoHeight);
    var pw = video.videoWidth * s;
    var ph = video.videoHeight * s;
    var ox = (w - pw) / 2;
    var oy = (h - ph) / 2;

    ctx.font = "600 14px Anuphan, sans-serif";

    // รอบที่ 1 : วาดกรอบทุกลูก (ขอบครีมรอบนอก + กรอบสีด้านใน แบบเดียวกับรูปผลตรวจ เห็นชัดทุกพื้นหลัง)
    for (var i = 0; i < boxes.length; i++) {
        var b = boxes[i];
        var x = ox + b.x1 * pw;
        var y = oy + b.y1 * ph;
        var bw = (b.x2 - b.x1) * pw;
        var bh = (b.y2 - b.y1) * ph;
        ctx.lineWidth = 6;
        ctx.strokeStyle = paperColor;
        ctx.strokeRect(x, y, bw, bh);
        ctx.lineWidth = 3;
        ctx.strokeStyle = liveColors[b.state];
        // สดแต่ควรดูอีกที : กรอบเส้นประ (แบบเดียวกับรูปผลตรวจ)
        if (b.check) {
            ctx.setLineDash([10, 6]);
        }
        ctx.strokeRect(x, y, bw, bh);
        ctx.setLineDash([]);
    }

    // รอบที่ 2 : วาดป้ายชื่อทีหลัง ป้ายจะไม่โดนเส้นกรอบของลูกอื่นทับ เช่น "ส้ม เน่า 91%"
    // จอแคบ (มือถือ) ใช้ป้ายสั้น "เน่า 91%" ไม่ใส่ชื่อผลไม้ ป้ายจะได้ไม่ชนกัน
    var drawn = [];   // ป้ายที่วาดไปแล้ว ไว้เช็กว่าป้ายใหม่ทับป้ายเก่าไหม
    for (var j = 0; j < boxes.length; j++) {
        var c = boxes[j];
        var label = liveWords[c.state] + " " + c.conf + "%";
        if (w >= 500) {
            label = c.thai + " " + label;
        }
        var lw = ctx.measureText(label).width + 12;
        var lx = ox + c.x1 * pw;
        var ly = oy + c.y1 * ph - 22;
        if (ly < 0) {
            ly = oy + c.y1 * ph;      // กรอบชิดขอบบน วางป้ายไว้ในกรอบแทน
        }
        // ทับป้ายเก่า ลองย้ายลงไปไว้ในกรอบ ถ้ายังทับอีก ไม่วาดป้ายนี้ (กรอบสียังบอกสด/เน่าอยู่)
        if (hitLabel(drawn, lx, ly, lw)) {
            ly = oy + c.y1 * ph;
            if (hitLabel(drawn, lx, ly, lw)) {
                continue;
            }
        }
        drawn.push({ x: lx, y: ly, w: lw });
        // ลูกสด = ป้ายพื้นครีม ตัวหนังสือเขียว / เน่า ตรวจซ้ำ = ป้ายพื้นทึบ (แบบเดียวกับเลขในรูปผลตรวจ)
        if (c.state == "good") {
            ctx.fillStyle = paperColor;
            ctx.fillRect(lx, ly, lw, 22);
            ctx.lineWidth = 2;
            ctx.strokeStyle = liveColors.good;
            ctx.strokeRect(lx + 1, ly + 1, lw - 2, 20);
            ctx.fillStyle = liveColors.good;
        } else {
            ctx.fillStyle = liveColors[c.state];
            ctx.fillRect(lx, ly, lw, 22);
            ctx.fillStyle = paperColor;
        }
        ctx.fillText(label, lx + 6, ly + 16);
    }
}

// เช็กว่าป้ายที่จะวาด (สูง 22) ทับป้ายที่วาดไปแล้วอันไหนไหม
function hitLabel(drawn, x, y, w) {
    for (var i = 0; i < drawn.length; i++) {
        var d = drawn[i];
        if (x < d.x + d.w && x + w > d.x && y < d.y + 22 && y + 22 > d.y) {
            return true;
        }
    }
    return false;
}


// สรุปใต้ภาพสด (เปลี่ยนข้อความเฉพาะตอนผลเปลี่ยน โปรแกรมอ่านหน้าจอจะได้ไม่อ่านซ้ำรัวๆ)
function showLiveInfo(result) {
    var text = "";
    if (!result.ok) {
        text = "ตอนนี้ AI ตรวจไม่ได้ ลองใหม่อีกครั้ง หรือใช้ปุ่ม ถ่าย แทน";
    } else if (result.total == 0) {
        text = "ยังไม่เห็นผลไม้ เล็งให้เห็นทั้งลูก แสงพอ";
    } else {
        // บอกเฉพาะอันที่มี (ไม่ต้องอ่าน "เน่า 0" ทุกครั้ง)
        text = "เห็น " + result.total + " ลูก";
        if (result.good > 0) {
            text = text + " · สด " + result.good;
            if (result.check > 0 && result.check == result.good) {
                text = text + " (ควรดูอีกทีทุกลูก)";
            } else if (result.check > 0) {
                text = text + " (ควรดูอีกที " + result.check + ")";
            }
        }
        if (result.bad > 0) {
            text = text + " · เน่า " + result.bad;
        }
        if (result.unsure > 0) {
            text = text + " · ตรวจซ้ำ " + result.unsure;
        }
    }
    if (liveInfo.textContent != text) {
        liveInfo.textContent = text;
    }
    // เจอลูกเน่า แถบสรุปเป็นสีอิฐ ไม่ใช่สีเขียว
    if (result.ok && result.bad > 0) {
        liveInfo.classList.add("live-bad");
    } else {
        liveInfo.classList.remove("live-bad");
    }
}
