# LingJi Local Alpha — 真机运行验收报告

**日期**: 2026-07-20
**仓库**: wangduoyu001/lingji (feature/second-brain-memory)
**环境**: 本地 Windows 真机

---

## 1. 机器环境

| 项目 | 值 |
|------|-----|
| OS | Windows 11 |
| Python | 3.13.2 |
| Node.js | v24.15.0 |
| Rust/Cargo | **未安装** |
| Ollama | v0.32.0 (运行中, PID 6916) |
| GPU | NVIDIA GeForce RTX 4060 Ti (8188 MiB) |
| CUDA Driver | 595.79 |
| 工作目录 | D:\\codex\\lingji-second-brain |
| 仓库状态 | feature/second-brain-memory (与 origin 同步) |

## 2. 路径安全检查

| 检查项 | 结果 |
|--------|------|
| 数据库路径 | D:\\codex\\lingji-second-brain\\data\\ ✅ |
| 日志路径 | D:\\codex\\lingji-second-brain\\data\\logs\\ ✅ |
| 缓存路径 | D:\\codex\\lingji-second-brain\\data\\cache\\ ✅ |
| 模型路径 | D:\\codex\\lingji-second-brain\\data\\models\\ ✅ |
| 向量存储 | D:\\codex\\lingji-second-brain\\data\\vector\\ ✅ |
| C: 盘写入 | 无 ❌ (仅 Obsidian CLI 自动检测路径, 只读, 合法) |

**结论**: 所有运行时数据均位于 D: 盘。无违规 C: 盘写入。

## 3. 启动结果

| 服务 | 端口 | 状态 |
|------|------|------|
| Backend (uvicorn) | 127.0.0.1:8765 | ✅ 运行中 |
| Frontend (http.server) | 127.0.0.1:4322 | ✅ 运行中 |

### API 端点验证

| 端点 | 状态 |
|------|------|
| GET /health | ✅ 通过 |
| GET /memory/status | ✅ 通过 |
| GET /memory/list | ✅ 通过 |
| GET /system/status | ✅ 通过 |

**前端 UI**: Control Center Dashboard 正常渲染, 包含导航面板、状态 widget、Brain Dashboard 头部。

## 4. 模型 / GPU 状态

### Ollama 可用模型 (7个)

| 模型 | 大小 |
|------|------|
| bge-m3:latest | 2.2 GB |
| deepseek-r1:8b | 4.9 GB |
| llama3.1:8b | 4.7 GB |
| llama3.2:3b | 2.0 GB |
| nomic-embed-text:latest | 274 MB |
| qwen2.5:14b | 9.0 GB |
| qwen2.5:7b | 4.4 GB |

### GPU 状态

| 项目 | 值 |
|------|-----|
| GPU 型号 | NVIDIA GeForce RTX 4060 Ti |
| 显存总量 | 8188 MiB |
| 显存已用 | 1417 MiB |
| 显存空闲 | 6533 MiB |
| CUDA Driver | 595.79 |
| Embedding 模型 | bge-m3 (1024-dim, 通过 Ollama) |

## 5. 测试结果

| 指标 | 值 |
|------|-----|
| 总测试数 | 184 |
| Passed | **175** |
| Skipped | **9** |
| Failed | **0** |
| 耗时 | 24.70s |

### 跳过的测试 (9个)

- 与 PySide6 相关的 desktop UI 测试 (PySide6 未安装)
- 部分 second_brain 测试 (旧模块)

## 6. UI 验收

| 检查项 | 状态 |
|--------|------|
| Frontend 编译 | ✅ npm run build 通过 |
| Control Center Dashboard | ✅ 正常显示 |
| Brain Dashboard 头部 | ✅ 正常显示 |
| 导航面板 | ✅ 正常显示 |
| 状态 widget | ✅ 正常显示 |

### 截图

- storage/reports/local-alpha/frontend-main.png — 主界面
- storage/reports/local-alpha/api-health.png — API 健康检查

## 7. 已知问题

| 问题 | 严重性 | 说明 |
|------|--------|------|
| Rust/Cargo 未安装 | P3 | 阻塞 Tauri 桌面构建 |
| PySide6 未安装 | P3 | 阻塞传统 Python desktop UI |
| C: 盘可用空间 | 低 | 31.9 GB 剩余, 建议清理 |

## 8. 验收结论

**总体结果: ✅ PASSED**

- ✅ 环境配置正确
- ✅ 路径安全合规 (全部 D: 盘)
- ✅ Backend 启动成功, 所有 API 通过
- ✅ Frontend 编译运行正常
- ✅ 175 测试通过, 0 失败
- ✅ GPU / Embedding 模型正常

**阻挡项**: 无

**建议**:
1. 安装 Rust/Cargo 以完成 Tauri 桌面构建
2. 如需桌面 UI, 安装 PySide6
3. 补充 P3 级别的 Model Center / CPU 检测 / CUDA 解析优化
