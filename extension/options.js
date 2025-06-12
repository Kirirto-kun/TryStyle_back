const apiInput = document.getElementById("api");
const tokenInput = document.getElementById("token");
const saveBtn = document.getElementById("save");

// Load saved values
chrome.storage.sync.get(["closetmind_token", "closetmind_api"], (res) => {
  apiInput.value = res.closetmind_api || "http://localhost:8000";
  tokenInput.value = res.closetmind_token || "";
});

saveBtn.addEventListener("click", () => {
  chrome.storage.sync.set(
    {
      closetmind_token: tokenInput.value,
      closetmind_api: apiInput.value,
    },
    () => {
      alert("Settings saved!");
    }
  );
}); 