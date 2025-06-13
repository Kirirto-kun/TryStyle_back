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

    try {
      // Check if chrome.runtime is still available
      if (!chrome.runtime) {
        console.warn("ClosetMind: Extension context invalidated. Please refresh the page.");
        return;
      }

      // Ask background to capture the visible tab
      chrome.runtime.sendMessage({ type: "CAPTURE_VISIBLE_TAB" }, (response) => {
        if (chrome.runtime.lastError) {
          console.error("ClosetMind:", chrome.runtime.lastError);
          return;
        }
        if (response && response.error) {
          console.error("ClosetMind:", response.error);
          return;
        }
        if (response && response.screenshot) {
          cropAndSend(response.screenshot, rect);
        }
      });
    } catch (err) {
      console.warn("ClosetMind: Extension error. Please refresh the page.", err);
      removeOverlay();
    }
  }

  function compressImage(dataUrl, maxWidth = 1200, quality = 0.8) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        let width = img.width;
        let height = img.height;

        // Calculate new dimensions if image is too large
        if (width > maxWidth) {
          height = Math.floor(height * (maxWidth / width));
          width = maxWidth;
        }

        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, width, height);
        resolve(canvas.toDataURL("image/jpeg", quality));
      };
      img.src = dataUrl;
    });
  }

  function cropAndSend(fullDataUrl, rect) {
    try {
      const img = new Image();
      img.onload = async () => {
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
        
        // Compress the image before uploading
        const compressedDataUrl = await compressImage(croppedDataUrl);
        uploadScreenshot(compressedDataUrl);
      };
      img.src = fullDataUrl;
    } catch (err) {
      console.error("ClosetMind: Error processing screenshot:", err);
    }
  }

  function uploadScreenshot(dataUrl) {
    chrome.storage.sync.get(["closetmind_token", "closetmind_api"], (res) => {
      if (chrome.runtime.lastError) {
        console.error("ClosetMind:", chrome.runtime.lastError);
        return;
      }

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
        mode: "cors",
        body: JSON.stringify({ image_base64: dataUrl }),
      })
        .then(async (r) => {
          if (!r.ok) {
            const errorText = await r.text();
            throw new Error(`HTTP ${r.status}: ${errorText}`);
          }
          return r.json();
        })
        .then((data) => {
          console.log("ClosetMind uploaded:", data);
          // Optional: Show success message to user
          const notification = document.createElement("div");
          notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #4CAF50;
            color: white;
            padding: 12px 24px;
            border-radius: 4px;
            z-index: 999999;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
          `;
          notification.textContent = "Screenshot uploaded successfully!";
          document.body.appendChild(notification);
          setTimeout(() => notification.remove(), 3000);
        })
        .catch((err) => {
          console.error("ClosetMind upload failed:", err);
          let errorMessage = "Failed to upload screenshot. ";
          if (err.message.includes("413")) {
            errorMessage += "The image is too large. Please try selecting a smaller area.";
          } else if (err.message.includes("CORS")) {
            errorMessage += "CORS error. Please check your API settings.";
          } else {
            errorMessage += "Please check your connection and token.";
          }
          alert(errorMessage);
        });
    });
  }

  // Add instruction overlay style on page load via CSS (injected through overlay.css)
  try {
    document.addEventListener("mousedown", mouseDownHandler);
  } catch (err) {
    console.error("ClosetMind: Failed to initialize event listeners:", err);
  }
})(); 