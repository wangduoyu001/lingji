---
title: "farion1231/cc-switch"
date: 2026-06-17
github: https://github.com/farion1231/cc-switch
stars: 44000
interest: 1
status: 未试
usable: 待评估
category: AI编程工具
实际用途: Codex/Claude 快速切换工具
tags:
  - GitHub
  - AI项目
  - AI编程工具
---

# CC Switch

> ⭐ 44,000 | 📅 2026-06-17 | [GitHub](https://github.com/farion1231/cc-switch)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

CC Switch 是一个桌面应用软件，专门解决"同时用多个 AI 编程工具时配置乱成一团"的问题。就像你家里有多个遥控器（电视、空调、音响），CC Switch 就是一个"万能遥控器"，把一个界面管理所有 AI 工具的配置。

具体来说，如果你同时用 Claude Code、Codex、Gemini CLI 这几个 AI 编程工具，每个工具都有自己的 API 配置、MCP 服务器（让 AI 能访问外部工具的接口）、Skills（技能包），切换不同 API 提供商（比如从 Anthropic 换到 OpenAI）时，要手动改好几个配置文件。CC Switch 把这些配置都集中到一个可视化界面里，点几下就能切换，不用手动改文件。

它支持 7 款 AI 工具（Claude Code、Claude Desktop、Codex、Gemini CLI、OpenCode、OpenClaw、Hermes Agent），内置 50+ 个 API 提供商预设（包括国内的 SiliconFlow、DeepSeek 等），也支持自定义。换 API 不用手动改 JSON 文件，在界面上点几下就行。

## 能实现什么效果

最直观的效果是：你要在 Claude Code 和 Codex 之间切换 API 提供商时，原来需要手动编辑 `~/.claude/settings.json` 和 `~/.codex/config.toml` 两个文件，改完还得重启终端。用了 CC Switch，在图形界面上选一下提供商，点"启用"，Claude Code 甚至支持热切换（不用重启），几秒钟搞定。对于一个同时用 3 个以上 AI 编程工具的人，每天能省 10-15 分钟找配置文件、改配置的时间。

另一个实用效果是"配置同步"：你在公司电脑和家里电脑都装了 Claude Code，原来要两边手动配同样的 MCP 服务器、Skills、提示词，很麻烦。CC Switch 支持云同步（通过 Dropbox、OneDrive、iCloud 或 WebDAV），配置存在云端，换台电脑打开 CC Switch 自动同步，不用重新配。对有多台开发设备的人来说，这个功能能省好几小时的重复配置时间。

成本追踪功能也很实用：CC Switch 有个用量仪表盘，能追踪每个模型的花费、请求次数、Token 使用量，还能看趋势图。原来你要去各个 API 提供商的网站上看账单，现在在一个界面就能看到所有 AI 工具的花费汇总，方便控制成本。

## 怎么用

- **首次安装**：去 GitHub Releases 页面（https://github.com/farion1231/cc-switch/releases/latest）下载对应系统的安装包。Windows 用户下载 `.msi` 安装包或便携版 `.zip`，Mac 用户推荐用 Homebrew：`brew install --cask cc-switch`，Linux 用户下载 `.deb` 或 `.rpm`
- **添加 API 提供商**：打开 CC Switch → 点"添加提供商" → 从 50+ 预设里选（比如"Anthropic"、"OpenAI"）或创建自定义配置 → 填写 API Key → 启用
- **切换提供商**：主界面选提供商 → 点"启用"（Claude Code 热切换生效，其他工具需要重启终端）。也可以从系统托盘（电脑右下角/右上角的图标）直接切换，不用打开主窗口
- **管理 MCP / 提示词 / 技能**：点对应按钮 → 添加/编辑/删除 → 选择要同步到哪些 AI 工具（可以只同步到 Claude Code，也可以同时同步到 Codex 和 Gemini）
- **恢复官方登录**：如果切换第三方 API 后想换回官方登录，从预设列表添加"官方登录"配置，切换后按官方工具的登出/登入流程操作即可

## 运行位置

- 🖥️ **Windows 10+、macOS 12+、Linux 主流发行版**都可以，是桌面应用软件（不是命令行工具）
- 基于 Tauri 2 框架构建（用 Rust 写后端，前端用 React），安装包体积小（约 11MB），启动快
- 不需要联网也能用（配置的切换在本地完成），但切换后 AI 工具本身需要联网调用 API

## 需要准备什么

- 💰 **要钱吗**：完全免费，开源（MIT 协议），没有任何付费功能。作者靠 API 中继服务商的赞助支持开发
- 📦 **需要准备什么**：什么都不需要，下载安装包安装就能用。但要管理的 AI 工具（Claude Code 等）需要各自配置好能正常运行
- 💻 **电脑配置**：要求很低，2015 年以后的电脑都能跑。Windows 10、macOS 12、Ubuntu 22.04 及以上都支持
- 🌐 **网络**：CC Switch 本身不需要网络，但你用的 AI 工具（Claude Code 等）需要能访问各自的 API 服务器

## 配合什么软件

- **管理的对象**：Claude Code、Claude Desktop、Codex、Gemini CLI、OpenCode、OpenClaw、Hermes Agent（共 7 款）
- **可配合的 API 提供商**：Anthropic、OpenAI、Google、DeepSeek、SiliconFlow、Kimi、MiniMax 等 50+ 家（国内外都有）
- **云同步**：可以配合 Dropbox、OneDrive、iCloud、NAS、WebDAV 服务器实现配置同步
- **独立使用**：CC Switch 本身是完整的管理工具，不需要其他软件也能用

## 客观评价

**优点**：
- 解决了一个真实痛点：同时用多个 AI 编程工具的人，配置管理真的很麻烦，这个工具彻底解决了
- 界面做得好，可视化配置比手动改 JSON/TOML 文件直观太多，新手也能上手
- 支持 7 款工具、50+ 提供商预设，覆盖面广，国内外主流 API 都内置了
- 云同步功能对于有多台开发设备的人非常实用
- 开源免费（MIT 协议），代码透明，没有隐藏收费
- 体积小（约 11MB）、启动快，不占系统资源
- 支持中文界面（已完成简体中文、繁体中文、日语、德语的 i18n 翻译）

**缺点/坑**：
- 需要切换多个 AI 编程工具的人才有用，如果你只用 Claude Code 一个工具，这个软件对你来说多余
- 部分 AI 工具切换提供商后需要重启终端才能生效（不是 CC Switch 的问题，是那些工具本身的限制）
- 项目比较新（目前约 44000 Star），可能还有 Bug，遇到问题需要去 GitHub Issues 找解决方案
- 国内有些 API 提供商没有预设，需要手动配置（不过界面上有向导，不太难）
- 信息有限：我无法实际使用它，以上评价基于 README 和搜索结果，可能有遗漏

**适合谁**：同时用 2 个以上 AI 编程工具（Claude Code + Codex + Gemini CLI 等）的开发者，或者经常需要切换 API 提供商的人。

**不适合谁**：只用一款 AI 编程工具的人（用不上它的核心功能）、不喜欢桌面应用只想用命令行的人。

**评分**：8/10 — 解决真实痛点，就是适用人群有限

## 未来趋势

- 📈 **所处阶段**：快速增长期。2026 年 4 月项目还只有约 44000 Star，目前仍在快速增长中
- 🔮 **6-12 个月走向**：预计会支持更多 AI 编程工具（目前 7 款，可能扩展到 10+ 款），云同步功能会更稳定，可能会加入"配置分享"功能（把自己配好的配置导出分享给别人）
- ⭐ **关注度**：4/5 — 在 AI 编程工具用户圈子里很火，但受众相对窄（只限于多工具用户）

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-17 | 重写为8字段富描述版本 | 44000 |
| 2026-06-16 | 首次记录（stars 数据有误，已修正） | 102000 |

---

*记录时间: 2026-06-17*
