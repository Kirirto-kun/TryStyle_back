(function () {
  let startX, startY, selectionBox;

  function createOverlay() {
    selectionBox = document.createElement("div");
    selectionBox.id = "closetmind-selection-box";
    document.body.appendChild(selectionBox);
  }

  function removeOverlay() {
    if (selectionBox) {
      selectionBox.remove();
      selectionBox = null;
    }
  }

  function mouseDownHandler(e) {
    if (e.button !== 0 || e.altKey === false) return; // Hold ALT + mouse drag to start

    startX = e.clientX;
    startY = e.clientY;
    createOverlay();
    selectionBox.style.left = `${startX}px`;
    selectionBox.style.top = `${startY}px`;

    document.addEventListener("mousemove", mouseMoveHandler);
    document.addEventListener("mouseup", mouseUpHandler, { once: true });
  }

  function mouseMoveHandler(e) {
    const width = Math.abs(e.clientX - startX);
    const height = Math.abs(e.clientY - startY);
    selectionBox.style.width = `${width}px`;
    selectionBox.style.height = `${height}px`;
    selectionBox.style.left = `${Math.min(e.clientX, startX)}px`;
    selectionBox.style.top = `${Math.min(e.clientY, startY)}px`;
  }

  function mouseUpHandler(e) {
    document.removeEventListener("mousemove", mouseMoveHandler);

    const rect = selectionBox.getBoundingClientRect();
    removeOverlay();

    // Ask background to capture the visible tab
    chrome.runtime.sendMessage({ type: "CAPTURE_VISIBLE_TAB" }, (response) => {
      if (response.error) {
        console.error(response.error);
        return;
      }
      cropAndSend(response.screenshot, rect);
    });
  }

  function cropAndSend(fullDataUrl, rect) {
    const img = new Image();
    img.onload = () => {
      const scale = window.devicePixelRatio;
      const canvas = document.createElement("canvas");
      canvas.width = rect.width * scale;
      canvas.height = rect.height * scale;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(
        img,
        rect.left * scale,
        rect.top * scale,
        rect.width * scale,
        rect.height * scale,
        0,
        0,
        rect.width * scale,
        rect.height * scale
      );
      const croppedDataUrl = canvas.toDataURL("image/png");
      uploadScreenshot(croppedDataUrl);
    };
    img.src = fullDataUrl;
  }

  function uploadScreenshot(dataUrl) {
    chrome.storage.sync.get(["closetmind_token", "closetmind_api"], (res) => {
      const token = res.closetmind_token || "";
      const api = res.closetmind_api || "http://localhost:8000";
      if (!token) {
        alert("ClosetMind: please set your API token in the extension options page.");
        return;
      }
      fetch(`${api}/waitlist/upload-screenshot`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ image_base64: dataUrl }),
      })
        .then((r) => r.json())
        .then((data) => console.log("ClosetMind uploaded", data))
        .catch((err) => console.error("Upload failed", err));
    });
  }

  // Add instruction overlay style on page load via CSS (injected through overlay.css)

  document.addEventListener("mousedown", mouseDownHandler);
})(); 