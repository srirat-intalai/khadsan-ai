// JavaScript ของหน้าเว็บ KhadSan AI
// ทำ 6 อย่าง : 1) โชว์รูปตัวอย่าง 2) เตือนไฟล์ใหญ่ 3) ปุ่มกำลังตรวจ (กดซ้ำไม่ได้)
//   4) เปิดกล้อง/ถ่ายรูป 5) ติ๊กขั้นตอนก่อนโชว์ผล 6) สแกนสด
// ปิด JavaScript เว็บยังส่งรูปและเห็นผลได้ปกติ

var page = document.documentElement;
var live = document.getElementById("live");      // ข้อความให้โปรแกรมอ่านหน้าจอ
var steps = document.querySelectorAll(".step");

// หน้าเว็บมีฟอร์มใส่รูปแค่อันเดียว
var form = document.querySelector(".scan-form");
var input = form.querySelector('input[type="file"]');
var drop = form.querySelector(".drop");
var warn = form.querySelector(".drop-warn");
var button = form.querySelector(".scan-btn");
var maxMb = Number(form.getAttribute("data-max-mb"));
var preview = null;   // รูปตัวอย่าง สร้างตอนเลือกรูปครั้งแรก

// กรอบสแกนของหน้าเริ่มต้น (ไม่มี = อยู่หน้าผล)
var stage = document.querySelector(".frame-empty");
var stageSub = document.querySelector(".frame-sub");


// ----- 1) และ 2) ตอนเลือกรูป -----
input.addEventListener("change", function () {
    var file = input.files[0];
    warn.hidden = true;
    input.setCustomValidity("");   // ล้างข้อความเตือนเก่า

    // ไม่ได้เลือกรูป (กดยกเลิก)
    if (!file) {
        if (preview) {
            preview.hidden = true;
        }
        return;
    }

    // ไฟล์ใหญ่เกิน : ไม่ให้ส่ง (เซิร์ฟเวอร์ก็เช็กซ้ำ)
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

    // สร้างรูปตัวอย่างครั้งเดียว
    if (!preview) {
        preview = document.createElement("img");
        preview.alt = "รูปที่เลือกไว้";
        // เปิดรูปไม่ได้ (เช่น HEIC) ไม่โชว์ตัวอย่าง แต่ยังส่งตรวจได้
        preview.addEventListener("error", function () {
            preview.hidden = true;
        });
        if (stage) {
            // หน้าเริ่มต้น : โชว์ในกรอบสแกนใหญ่
            preview.className = "frame-photo";
            stage.insertBefore(preview, stage.firstChild);
            stage.classList.add("has-img");
        } else {
            // หน้าผลตรวจ : โชว์รูปเล็กในช่องเลือกรูป
            preview.className = "preview";
            drop.appendChild(preview);
        }
    }

    // คืนหน่วยความจำของรูปเก่า แล้วโชว์รูปใหม่
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
    // กดซ้ำไม่ส่งซ้ำ
    if (form.classList.contains("is-busy")) {
        event.preventDefault();
        return;
    }
    form.classList.add("is-busy");
    page.classList.add("busy-page");          // มุมกรอบสแกนกะพริบ
    button.setAttribute("aria-disabled", "true");
    closeCamera();   // ปิดกล้อง ไฟกล้องจะดับ

    // ขั้นตอน : 1 เสร็จ / 2 กำลังทำ
    for (var i = 0; i < steps.length; i++) {
        steps[i].classList.remove("now");
    }
    if (steps.length == 3) {
        steps[1].classList.add("now");
        // หน้าเริ่มต้น : ขั้นที่ 1 เป็นติ๊ก "ส่งแล้ว" (ใส่ sent ไว้ กด Back จะคืนค่าให้)
        if (!steps[0].classList.contains("step-done")) {
            oldStepClass = steps[0].className;
            oldStepText = steps[0].querySelector(".mark-text").textContent;
            steps[0].className = "step step-done sent";
            steps[0].querySelector(".mark-text").textContent = "ส่งแล้ว";
        }
    }
    // ข้อความในกรอบสแกน เปลี่ยนเป็นกำลังตรวจ
    if (stageSub) {
        stageSub.textContent = "รูปที่เลือก · AI กำลังตรวจ…";
    }
    live.textContent = "ส่งรูปแล้ว AI กำลังตรวจ รอสักครู่";
});
var oldStepClass = "";
var oldStepText = "";


// กด Back กลับมา บางเบราว์เซอร์จำหน้าเดิม ปุ่มค้าง "กำลังตรวจ" เลยคืนค่าให้
window.addEventListener("pageshow", function () {
    form.classList.remove("is-busy");
    page.classList.remove("busy-page");
    button.removeAttribute("aria-disabled");
    for (var i = 0; i < steps.length; i++) {
        steps[i].classList.remove("now");
    }
    // คืนติ๊ก "ส่งแล้ว" เป็นแบบเดิม
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
var stream = null;   // ภาพจากกล้อง (null = ปิด)

// โชว์ปุ่มเปิดกล้องเฉพาะเบราว์เซอร์ที่ทำได้ (ต้องเป็น https หรือ localhost)
if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    camRow.hidden = false;
}

function showCamMsg(text) {
    camMsg.textContent = text;
    camMsg.hidden = false;
}

// ปิดกล้อง : หยุดสแกนสด ไฟกล้องดับ โชว์ปุ่มเปิดกล้อง
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
    // environment = กล้องหลังมือถือ (คอมได้เว็บแคม)
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
            // บอกเหตุผลเป็นภาษาไทย ให้ใช้ปุ่มเลือกรูปแทน
            if (err.name == "NotAllowedError") {
                showCamMsg("เบราว์เซอร์ยังไม่ให้ใช้กล้อง กดอนุญาตกล้อง หรือใช้ปุ่มเลือกรูปจากเครื่องแทน");
            } else if (err.name == "NotFoundError" || err.name == "OverconstrainedError") {
                showCamMsg("ไม่เจอกล้องในเครื่องนี้ ใช้ปุ่มเลือกรูปจากเครื่องแทนนะ");
            } else {
                showCamMsg("เปิดกล้องไม่ได้ (กล้องอาจถูกแอปอื่นใช้อยู่) ใช้ปุ่มเลือกรูปจากเครื่องแทนนะ");
            }
        });
});

// จอคอม หน้าเริ่มต้น : ย้ายภาพกล้องไปไว้ในกรอบสแกนใหญ่
// มือถือ : ไม่ย้าย ซ่อนการ์ดกรอบสแกนแทน (ภาพกล้องจะได้อยู่ใกล้ปุ่ม)
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
        // แถบนับลูกย้ายไปใต้ภาพกล้องด้วย
        stage.parentNode.insertBefore(liveInfo, stage.nextSibling);
        stageSub.textContent = "ภาพจากกล้อง · กดถ่าย หรือสแกนสด ทางซ้าย";
    } else {
        // มือถือ : ซ่อนการ์ดกรอบสแกน
        stage.parentNode.classList.add("cam-up");
    }
    camMoved = true;
}
// ปิดกล้องแล้ว ย้ายภาพกล้องกลับที่เดิม คืนข้อความในกรอบ
function camBack() {
    if (!camMoved) {
        return;
    }
    if (stage.classList.contains("has-cam")) {
        cam.insertBefore(camStage, cam.firstChild);
        cam.insertBefore(liveInfo, camStage.nextSibling);
    }
    stage.classList.remove("has-cam");
    stage.parentNode.classList.remove("cam-up");
    stageSub.textContent = stageSubText;
    camMoved = false;
}

// กด "ถ่าย" : ทำภาพตอนนั้นเป็น jpg ใส่ช่องเลือกรูป
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
        // ปิดกล้องก่อน แล้วค่อยใส่รูปที่ถ่าย
        closeCamera();
        try {
            var file = new File([blob], "camera.jpg", { type: "image/jpeg" });
            var box = new DataTransfer();   // ใช้ยัดไฟล์เข้าช่องเลือกรูป
            box.items.add(file);
            input.files = box.files;
            input.dispatchEvent(new Event("change"));   // ให้ข้อ 1) ทำรูปตัวอย่าง
            // เลื่อนไปที่ปุ่มตรวจ
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

// เลือกรูปจากเครื่องตอนกล้องเปิด = ปิดกล้อง
input.addEventListener("click", function () {
    closeCamera();
});


// ----- 5) ได้ผลแล้ว : ติ๊กขั้นตอนทีละขั้น แล้วค่อยโชว์ผล -----
// เล่นเมื่อ html มี class "play" (มีผลตรวจ)
// ครั้งแรกเล่นช้าๆ ~5 วิ ให้เห็นว่า AI ทำอะไร / ครั้งต่อไปไม่ถึง 1 วิ
var stepTimes = [800, 2000, 2200];
var stepIndex = 0;
var timer = null;
var skipRow = document.querySelector(".skip-row");

function nextStep() {
    // ขั้นก่อนหน้า : เลิกหมุน โชว์ติ๊ก
    if (stepIndex > 0) {
        steps[stepIndex - 1].classList.remove("now");
        steps[stepIndex - 1].classList.add("shown");
    }
    // ขั้นต่อไป : หมุน แล้วรอ
    if (stepIndex < steps.length) {
        steps[stepIndex].classList.add("now");
        timer = setTimeout(nextStep, stepTimes[stepIndex]);
        stepIndex = stepIndex + 1;
    } else {
        showResult();
    }
}

// โชว์ผลทั้งหมด (เล่นจบ หรือกด "ดูผลทันที")
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
    // จำว่าเคยดูแล้ว เฉพาะตอนได้ดูจริง (ถ้าจำตั้งแต่หน้าแรก ผลครั้งแรกจะเล่นแบบเร็วไปเลย)
    try {
        if (localStorage.getItem("khadsan-seen-steps") == "yes") {
            stepTimes = [200, 250, 250];
        }
        localStorage.setItem("khadsan-seen-steps", "yes");
    } catch (e) {
        // เบราว์เซอร์ไม่ให้จำ (โหมดไม่ระบุตัวตน) ก็เล่นเต็ม
    }
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
var sendCanvas = document.createElement("canvas");   // ไว้ย่อภาพก่อนส่ง (ไม่โชว์)
var liveOn = false;
var liveTimer = null;

// สีกรอบ อ่านจาก style.css
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

// ส่งภาพทีละภาพ ผลกลับมาค่อยส่งภาพต่อไป (เน็ตช้าก็ไม่ค้าง)
function sendFrame() {
    if (!liveOn) {
        return;
    }
    // กล้องยังไม่พร้อม หรือสลับแอปอยู่ รอแล้วลองใหม่
    if (!stream || video.videoWidth == 0 || document.hidden) {
        liveTimer = setTimeout(sendFrame, 300);
        return;
    }
    // ย่อด้านยาวไม่เกิน 640 ส่งเร็วขึ้น
    var scale = Math.min(1, 640 / Math.max(video.videoWidth, video.videoHeight));
    sendCanvas.width = Math.round(video.videoWidth * scale);
    sendCanvas.height = Math.round(video.videoHeight * scale);
    sendCanvas.getContext("2d").drawImage(video, 0, 0, sendCanvas.width, sendCanvas.height);

    sendCanvas.toBlob(function (blob) {
        // แปลงภาพไม่ได้ (กล้องเพิ่งปิด) ข้าม
        if (!blob) {
            liveTimer = setTimeout(sendFrame, 300);
            return;
        }
        var data = new FormData();
        data.append("frame", blob, "frame.jpg");
        // รอผลไม่เกิน 8 วิ เกินแล้วยกเลิก ส่งภาพใหม่
        var waiting = new AbortController();
        var giveUp = setTimeout(function () {
            waiting.abort();
        }, 8000);
        fetch(liveUrl, { method: "POST", body: data, signal: waiting.signal })
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
                clearTimeout(giveUp);
                // ผลมาหรือพัง ก็เว้นนิดนึงแล้วส่งภาพต่อไป
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

    // ภาพกล้องไม่บีบ (อาจมีขอบว่าง) หาตำแหน่งภาพจริงก่อน
    var s = Math.min(w / video.videoWidth, h / video.videoHeight);
    var pw = video.videoWidth * s;
    var ph = video.videoHeight * s;
    var ox = (w - pw) / 2;
    var oy = (h - ph) / 2;

    ctx.font = "600 14px Anuphan, sans-serif";

    // รอบ 1 : กรอบทุกลูก (ขอบครีม + สีด้านใน แบบรูปผลตรวจ)
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
        // สดแต่ควรดูอีกที : เส้นประ
        if (b.check) {
            ctx.setLineDash([10, 6]);
        }
        ctx.strokeRect(x, y, bw, bh);
        ctx.setLineDash([]);
    }

    // รอบ 2 : ป้าย เช่น "ส้ม เน่า 91%" (วาดทีหลัง จะไม่โดนกรอบอื่นทับ)
    // จอแคบใช้ป้ายสั้น "เน่า 91%"
    var drawn = [];   // ป้ายที่วาดแล้ว ไว้เช็กว่าทับกันไหม
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
            ly = oy + c.y1 * ph;      // กรอบชิดขอบบน วางป้ายในกรอบ
        }
        // ทับป้ายเก่า ย้ายลงในกรอบ ยังทับอีกก็ไม่วาด (สีกรอบยังบอกสด/เน่า)
        if (hitLabel(drawn, lx, ly, lw)) {
            ly = oy + c.y1 * ph;
            if (hitLabel(drawn, lx, ly, lw)) {
                continue;
            }
        }
        drawn.push({ x: lx, y: ly, w: lw });
        // สด = ป้ายครีมตัวเขียว / อื่นๆ = ป้ายทึบ
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

// ป้ายใหม่ (สูง 22) ทับป้ายที่วาดแล้วไหม
function hitLabel(drawn, x, y, w) {
    for (var i = 0; i < drawn.length; i++) {
        var d = drawn[i];
        if (x < d.x + d.w && x + w > d.x && y < d.y + 22 && y + 22 > d.y) {
            return true;
        }
    }
    return false;
}


// สรุปใต้ภาพสด (เปลี่ยนเฉพาะตอนผลเปลี่ยน โปรแกรมอ่านหน้าจอจะไม่อ่านรัว)
function showLiveInfo(result) {
    var text = "";
    if (!result.ok) {
        text = "ตอนนี้ AI ตรวจไม่ได้ ลองใหม่อีกครั้ง หรือใช้ปุ่ม ถ่าย แทน";
    } else if (result.total == 0) {
        text = "ยังไม่เห็นผลไม้ เล็งให้เห็นทั้งลูก แสงพอ";
    } else {
        // บอกเฉพาะอันที่มี
        text = "เห็น " + result.total + " ลูก";
        if (result.good > 0) {
            text = text + " · สด " + result.good;
            if (result.check > 0 && result.check == result.good) {
                text = text + " (ควรดูอีกที ทุกลูก)";
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
    // เจอลูกเน่า แถบเป็นสีอิฐ
    if (result.ok && result.bad > 0) {
        liveInfo.classList.add("live-bad");
    } else {
        liveInfo.classList.remove("live-bad");
    }
}
