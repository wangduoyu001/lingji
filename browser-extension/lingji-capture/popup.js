const status = document.getElementById("status");

document.getElementById("selection").addEventListener("click", () => capture("selection"));
document.getElementById("page").addEventListener("click", () => capture("page"));
document.getElementById("options").addEventListener("click", () => chrome.runtime.openOptionsPage());

function capture(mode) {
  status.textContent = "提交中…";
  chrome.runtime.sendMessage({ type: "lingji-capture", mode }, (response) => {
    if (chrome.runtime.lastError) {
      status.textContent = chrome.runtime.lastError.message;
      status.className = "error";
      return;
    }
    if (!response?.ok) {
      status.textContent = response?.error || "提交失败";
      status.className = "error";
      return;
    }
    status.textContent = "已提交到灵机";
    status.className = "success";
  });
}
