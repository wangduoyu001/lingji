const MENU_PAGE = "lingji-capture-page";
const MENU_SELECTION = "lingji-capture-selection";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({ id: MENU_PAGE, title: "将当前页面投喂到灵机", contexts: ["page"] });
    chrome.contextMenus.create({ id: MENU_SELECTION, title: "将选中文字投喂到灵机", contexts: ["selection"] });
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab?.id) return;
  try {
    const mode = info.menuItemId === MENU_SELECTION ? "selection" : "page";
    const payload = await collectPage(tab.id, mode);
    await submitToLingJi(payload);
    await setBadge("✓", "#287b5f");
  } catch (error) {
    console.error("LingJi capture failed", error);
    await setBadge("!", "#9e3f3f");
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "lingji-capture") return false;
  void (async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.id) throw new Error("No active tab");
      const payload = await collectPage(tab.id, message.mode || "page");
      const result = await submitToLingJi(payload);
      await setBadge("✓", "#287b5f");
      sendResponse({ ok: true, result });
    } catch (error) {
      await setBadge("!", "#9e3f3f");
      sendResponse({ ok: false, error: error instanceof Error ? error.message : String(error) });
    }
  })();
  return true;
});

async function collectPage(tabId, mode) {
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId },
    func: (captureMode) => {
      const selected = window.getSelection()?.toString().trim() || "";
      const description = document.querySelector('meta[name="description"]')?.getAttribute("content") || "";
      const author = document.querySelector('meta[name="author"]')?.getAttribute("content") || "";
      const canonical = document.querySelector('link[rel="canonical"]')?.getAttribute("href") || location.href;
      const articleText = document.querySelector("article")?.innerText?.trim() || "";
      const mainText = document.querySelector("main")?.innerText?.trim() || "";
      return {
        source_type: detectPlatform(location.hostname),
        platform: detectPlatform(location.hostname),
        title: document.title || location.hostname,
        url: canonical,
        author,
        description,
        selected_text: selected,
        text: captureMode === "selection" ? selected : (selected || articleText || mainText || document.body.innerText || "").slice(0, 500000),
        capture_method: `browser_extension_${captureMode}`,
      };

      function detectPlatform(hostname) {
        const host = hostname.toLowerCase();
        if (host.includes("mp.weixin.qq.com")) return "wechat_article";
        if (host.includes("xiaohongshu.com")) return "xiaohongshu";
        if (host.includes("douyin.com")) return "douyin";
        if (host.includes("bilibili.com")) return "bilibili";
        if (host.includes("youtube.com") || host.includes("youtu.be")) return "youtube";
        return "web";
      }
    },
    args: [mode],
  });
  return result;
}

async function submitToLingJi(payload) {
  const settings = await chrome.storage.local.get({
    baseUrl: "http://127.0.0.1:8766",
    token: "",
  });
  const response = await fetch(`${String(settings.baseUrl).replace(/\/$/, "")}/api/share`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(settings.token ? { "X-LingJi-Token": settings.token } : {}),
    },
    body: JSON.stringify(payload),
  });
  const text = await response.text();
  const result = text ? JSON.parse(text) : {};
  if (!response.ok) throw new Error(result.detail || response.statusText);
  return result;
}

async function setBadge(text, color) {
  await chrome.action.setBadgeBackgroundColor({ color });
  await chrome.action.setBadgeText({ text });
  setTimeout(() => chrome.action.setBadgeText({ text: "" }), 3000);
}
