# LingJi 灵机 — Local Alpha 开发路线图

## 项目定位
灵机 (LingJi) 是一款 AI 第二大脑系统，定位为 AI 编导 / AI 运营 / AI 研究员 / AI 商业策划。系统基于 Obsidian 知识库，提供记忆管道、本地模型调用、自动采集和智能分析能力。

## 当前状态 (Local Alpha)

### ✅ 已完成
- **硬件检测**: CPU/GPU/内存/磁盘完整检测，支持 WMI CPU 型号、nvidia-smi GPU 信息、CUDA 版本多源回退
- **模型中心**: Ollama 本地模型清单、兼容性标记、配置分配（含 :latest 标签规范化）
- **控制 API**: 36+ REST 端点，涵盖设置、硬件、模型、任务、存储、备份、验收
- **桌面 UI**: React 19 + Vite 7 + TypeScript 5.8，11 个页面（含脑状态看板）
- **测试**: 128 项自动化测试通过
- **Rust/Tauri**: Rust 1.97.1 已安装，Tauri 依赖包已锁定
- **文档**: 本路线图 + 内存管道设计文档

### 🔧 待完成
- [ ] Tauri 桌面构建（需 Visual Studio Build Tools）
- [ ] 实际软硬件验收报告集成
- [ ] GPU 模型兼容性加载测试
- [ ] 生产环境部署脚本
- [ ] 端到端 Playwright 浏览器验收测试

## 系统架构 (4层)

| 层 | 职责 | 目录 |
|---|---|---|
| L1 Data Layer | Obsidian Vault (不可变 Source of Truth) | `vault/` |
| L2 Index Layer | `pemis_index.json` (可重建) | `storage/` |
| L3 Logic Layer | Router + Safety Guard + Scheduler | `src/` |
| L4 Ops Layer | backup + journal + integrity + metrics | `src/storage/`, `src/acceptance/` |

## 构建与测试

```bash
# Python 测试
cd D:\codex\lingji-local-test
python -m pytest tests/ -v

# UI 构建
cd desktop\lingji-control
npm install
npx vite build

# Tauri 构建 (需要 VS Build Tools)
cd desktop\lingji-control
npx tauri build
```

## API 端点

- `GET /api/brain/status` — 脑状态看板 (记忆数、向量数、模型、GPU)
- `GET /api/overview` — 系统总览
- `GET /api/hardware/capabilities` — 硬件能力快照
- `GET /api/models` — 模型清单
- `GET /api/jobs` — 任务队列