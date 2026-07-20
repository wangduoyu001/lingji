const baseUrl = document.getElementById("baseUrl");
const token = document.getElementById("token");
const status = document.getElementById("status");

void chrome.storage.local.get({ baseUrl: "http://127.0.0.1:8766", token: "" }).then((values) => {
  baseUrl.value = values.baseUrl;
  token.value = values.token;
});

document.getElementById("save").addEventListener("click", async () => {
  await chrome.storage.local.set({ baseUrl: baseUrl.value.replace(/\/$/, ""), token: token.value.trim() });
  show("设置已保存", "success");
});

document.getElementById("test").addEventListener("click", async () => {
  try {
    const response = await fetch(`${baseUrl.value.replace(/\/$/, "")}/api/health`, {
      headers: token.value.trim() ? { "X-LingJi-Token": token.value.trim() } : {},
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || response.statusText);
    show(payload.healthy ? "连接成功，系统正常" : "连接成功，但健康检查有异常", payload.healthy ? "success" : "warning");
  } catch (error) {
    show(error instanceof Error ? error.message : String(error), "error");
  }
});

function show(text, className) {
  status.textContent = text;
  status.className = className;
}
