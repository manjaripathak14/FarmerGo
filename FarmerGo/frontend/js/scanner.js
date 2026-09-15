/* =========================================================
   scanner.js
   Logic for scanner.html. Uses the html5-qrcode library (loaded
   via CDN in scanner.html) to open the device camera and read QR
   codes — we do not implement any QR scanning logic ourselves.
   ========================================================= */

const officer = requireOfficerLogin();

const msgBox = document.getElementById("scan-message");
let isProcessing = false; // avoids submitting the same scan multiple times in a row

async function handleScannedCode(gatePassId) {
  if (isProcessing) return;
  isProcessing = true;

  clearMessage(msgBox);

  try {
    const result = await apiPost("/scan", { gate_pass_id: gatePassId.trim() });
    showMessage(
      msgBox,
      `${gatePassId} scanned successfully — moved to stage: ${stageLabel(result.new_stage)}.`,
      "success"
    );
  } catch (err) {
    showMessage(msgBox, err.message);
  }

  // Small delay before allowing the next scan, so the same QR code
  // isn't accidentally submitted twice in a row.
  setTimeout(() => { isProcessing = false; }, 2000);
}

function submitManualScan() {
  const input = document.getElementById("manual-id");
  const value = input.value.trim();
  if (!value) {
    showMessage(msgBox, "Please enter a Gate Pass ID.");
    return;
  }
  handleScannedCode(value);
  input.value = "";
}

// Try to start the camera scanner. If the library or camera isn't
// available (e.g. no HTTPS, no camera, or offline demo), we fail
// quietly and the officer can still use the manual entry box above.
function startCameraScanner() {
  if (typeof Html5Qrcode === "undefined") {
    showMessage(msgBox, "Camera scanner library not available — use manual entry below.", "info");
    return;
  }

  const scanner = new Html5Qrcode("reader");

  scanner.start(
    { facingMode: "environment" },
    { fps: 10, qrbox: 250 },
    (decodedText) => {
      handleScannedCode(decodedText);
    },
    () => {
      // Called continuously while no QR code is found — intentionally ignored.
    }
  ).catch(() => {
    showMessage(msgBox, "Could not access the camera — use manual entry below.", "info");
  });
}

startCameraScanner();
