const { Notice, Plugin, normalizePath } = require('obsidian');

const now = () => new Date().toISOString();
const safeStamp = () => new Date().toISOString().replace(/[:.]/g, '-');

module.exports = class LingJiControlPlugin extends Plugin {
  async onload() {
    this.addRibbonIcon('brain-circuit', '打开灵机控制中心', async () => {
      await this.openFile('00-System/Extraction-Center.md');
    });

    this.addCommand({
      id: 'open-extraction-center',
      name: '打开提取与采集中心',
      callback: () => this.openFile('00-System/Extraction-Center.md'),
    });
    this.addCommand({
      id: 'open-skills-center',
      name: '打开 Skill 管理中心',
      callback: () => this.openFile('00-System/Skills-Center.md'),
    });
    this.addCommand({
      id: 'new-chatgpt-import-request',
      name: '新建 ChatGPT 导入请求',
      callback: () => this.createChatGPTRequest(),
    });
    this.addCommand({
      id: 'new-web-capture-request',
      name: '新建网页/视频号采集请求',
      callback: () => this.createWebRequest(),
    });
    this.addCommand({
      id: 'new-skill-sync-request',
      name: '新建 Skill 同步请求',
      callback: () => this.createSkillRequest(),
    });

    this.addStatusBarItem().setText('灵机');
  }

  async createChatGPTRequest() {
    const body = `---
schema_version: 1
id: ""
title: ChatGPT 导入请求
memory_type: extraction_request
request_type: chatgpt_import
status: draft
privacy: private
input_path: "D:/exports/chatgpt.zip"
project: []
privacy_scan: true
force: false
created_at: ${now()}
updated_at: ${now()}
---

# ChatGPT 导入请求

1. 修改 \`input_path\`。
2. 填写项目。
3. 确认后将 \`status\` 改为 \`queued\`。
`;
    await this.createRequest('ChatGPT-Import', body);
  }

  async createWebRequest() {
    let clipboard = '';
    try {
      clipboard = await navigator.clipboard.readText();
    } catch (_) {}
    const isUrl = /^https?:\/\//i.test(clipboard.trim());
    const sourceUrl = isUrl ? clipboard.trim() : '';
    const capturedText = isUrl ? '' : clipboard.trim();
    const body = `---
schema_version: 1
id: ""
title: 网页或视频号采集请求
memory_type: extraction_request
request_type: web_capture
status: draft
privacy: private
source_type: video_channel
platform: video_channel
source_url: ${JSON.stringify(sourceUrl)}
account_name: ""
published_at: ""
duration_seconds: ""
cover_url: ""
media_url: ""
project: []
created_at: ${now()}
updated_at: ${now()}
---

# 网页或视频号采集请求

## 已复制内容

${capturedText}

## 操作

- 普通网页可将 \`source_type\` 改为 \`web\`。
- 公众号文章使用 \`wechat_article\`。
- 视频号使用 \`video_channel\`。
- 补充账号、简介、转写、OCR 或本地媒体路径。
- 确认后将 \`status\` 改为 \`queued\`。
`;
    await this.createRequest('Web-Capture', body);
  }

  async createSkillRequest() {
    const body = `---
schema_version: 1
id: ""
title: Skill 同步请求
memory_type: extraction_request
request_type: skill_sync
status: draft
privacy: private
input_path: "D:/codex/skills"
created_at: ${now()}
updated_at: ${now()}
---

# Skill 同步请求

1. 修改 \`input_path\` 为包含 SKILL.md 的目录。
2. 确认后将 \`status\` 改为 \`queued\`。
3. Skill 代码仍保留在 Git 或原目录，Obsidian 只管理清单与验证状态。
`;
    await this.createRequest('Skill-Sync', body);
  }

  async createRequest(prefix, content) {
    const folder = normalizePath('00-System/Extraction/Requests');
    if (!this.app.vault.getAbstractFileByPath(folder)) {
      await this.app.vault.createFolder(folder);
    }
    const path = normalizePath(`${folder}/${prefix}-${safeStamp()}.md`);
    const file = await this.app.vault.create(path, content);
    await this.app.workspace.getLeaf(true).openFile(file);
    new Notice('已创建请求。确认内容后将 status 改为 queued。');
  }

  async openFile(path) {
    const normalized = normalizePath(path);
    const file = this.app.vault.getAbstractFileByPath(normalized);
    if (!file) {
      new Notice(`未找到 ${normalized}，请先启动一次灵机服务。`);
      return;
    }
    await this.app.workspace.getLeaf(true).openFile(file);
  }
};
