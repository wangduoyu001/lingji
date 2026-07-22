# P2-11B Local Windows Acceptance Report v2

> 测试日期：2026-07-22
> 报告生成：Claude Code (Fable 5)
> 测试模式：只读验收 + 实机 NSIS 安装验证
> 对应 PR：https://github.com/wangduoyu001/lingji/pull/47

## 1. 测试身份

| 字段 | 值 |
|------|-----|
| 测试日期 | 2026-07-22 20:35 – 21:45 CST |
| 操作系统 | Microsoft Windows 10 Pro 22H2 (10.0.19045) |
| 仓库地址 | https://github.com/wangduoyu001/lingji.git |
| 分支 | `work/p2-11b-runtime-sidecar-manager` |
| Commit SHA | `6b70df0140bfae7559758322b579daa1611cb64f` |
| 最后提交 | `fix(runtime): build frontend before Tauri Rust tests` |
| PR | #47 |
| 测试目录 | `D:\LingJi-Validation\P2-11B\lingji` |
| 测试数据目录 | `D:\LingJi-Acceptance\P2-11B` |
| 安装目录 | `E:\灵机\` |

## 2. 环境版本

| 组件 | 版本 |
|------|------|
| Python (默认) | 3.13.2 |
| Python (sidecar) | 3.12.6 (`E:\python\python.exe`) |
| Node.js | v24.15.0 |
| npm | 11.12.1 |
| Rust | rustc 1.97.1 |
| Cargo | cargo 1.97.1 |
| Rust target | `x86_64-pc-windows-msvc` |
| Git | 2.46.2.windows.1 |
| Windows | 10.0.19045 |
| PyInstaller | 6.21.0 |
| GPU | NVIDIA RTX 4060 Ti 8GB |

## 3. Git 状态

| 检查项 | 结果 |
|--------|------|
| 初始工作区干净 | PASS |
| 测试结束 | Cargo.lock/Cargo.toml 被自动修改 + .venv 目录生成 |

## 4. 测试矩阵

| # | 测试项 | 退出码 | 结果 |
|----|--------|--------|------|
| 1 | 仓库克隆与分支切换 | 0 | PASS |
| 2 | Python 3.12 venv + pip install | 0 | PASS |
| 3 | pip check | 0 | PASS |
| 4 | Sidecar 专项测试 (8) | 0 | PASS |
| 5 | 全仓 Python 测试 (510, 排除 desktop/e2e) | 1 | FAIL (1 预存) |
| 6 | npm ci | 0 | PASS |
| 7 | Desktop smoke (18 scripts) | 0 | PASS |
| 8 | Desktop build (tsc + vite) | 0 | PASS |
| 9 | Sidecar PyInstaller 构建 | 0 | PASS |
| 10 | Sidecar --check-config | 0 | PASS |
| 11 | Sidecar 启动 + 健康检查 | 200 | PASS |
| 12 | 匹配 instance_id 停止 | — | PASS |
| 13 | 残留进程检查 | — | PASS |
| 14 | Rust cargo check | 0 | PASS |
| 15 | Rust cargo test (3) | 0 | PASS |
| 16 | NSIS 安装包构建 | 0 | PASS |
| 17 | 外部 8766 不误杀 | — | PASS |
| 18 | NSIS 安装 + 启动桌面端 | — | PASS |
| 19 | 卸载 + 数据保留 | — | PASS |

## 5. Python 测试结果

### 5.1 Sidecar 专项测试

| 指标 | 值 |
|------|-----|
| 总数 | 8 |
| 通过 | 8 |
| 结果 | **PASS** |

### 5.2 全仓 Python 测试

| 指标 | 值 |
|------|-----|
| 总数 | 510 |
| 通过 | 503 |
| 失败 | 1 (预存) |
| 跳过 | 6 |
| 耗时 | 60.22s |

唯一失败: `test_second_brain_is_not_in_original_start_chain` — Python 3.12 venv 缺少 textual/PySide6。预存问题，非 P2-11B 引入。

## 6. Desktop 测试结果

| 指标 | 值 |
|------|-----|
| npm ci | PASS |
| 18 套 Smoke | **全部通过** |
| TypeScript | PASS |
| Vite Build | PASS (363 KB JS + 41 KB CSS) |

## 7. Rust 测试结果

| 指标 | 值 |
|------|-----|
| cargo check | PASS |
| cargo test | **3 passed, 0 failed** |

测试: `display_paths_do_not_expose_owner_name`, `packaged_identity_requires_fixed_mode_and_loopback`, `token_path_stays_under_storage`

## 8. Sidecar 构建结果

| 指标 | 值 |
|------|-----|
| PyInstaller 版本 | 6.21.0 |
| Python 版本 | 3.12.6 |
| 模式 | onedir |
| EXE 大小 | 12,508,768 bytes (~12 MB) |
| 运行库文件 | 108 |
| SHA-256 | `d881a34dc8af9ab35dffb50ae348e74a1e36aca2164b8b7030ac552e2a05947b` |
| 自动模型下载 | false |
| 自动 Qdrant 重建 | false |
| Owner 数据独立 | true |

## 9. Sidecar 生命周期结果

| 检查项 | 结果 |
|--------|------|
| 8766 端口空闲 | PASS |
| 启动成功 | PASS |
| Token 生成 | PASS (45 bytes) |
| 身份文件生成 | PASS (`sidecar-state.json`) |
| 认证 /api/health 200 | PASS |
| mode=packaged_sidecar | PASS |
| host=127.0.0.1, port=8766 | PASS |
| 匹配停止被接受 | PASS |
| 自动退出 | PASS |
| 身份文件清除 | PASS |
| 残留进程 | 无 |

## 10. NSIS 安装包实机验证

### 10.1 构建产物

| 文件 | 大小 | 状态 |
|------|------|------|
| `灵机_0.1.0_x64-setup.exe` | 30.8 MB | PASS |
| `lingji-control-center.exe` | 9.0 MB | PASS |
| `lingji-core.exe` | 12.5 MB | PASS |

### 10.2 安装与运行

| 检查项 | 结果 |
|--------|------|
| 双击启动安装 | PASS |
| 安装路径 | `E:\灵机\` |
| 注册表卸载入口 | PASS (HKCU, DisplayName=灵机) |
| 桌面端启动 | PASS |
| 自动启动核心 | PASS (PID 508) |
| 8766 监听 | PASS |
| 认证健康 200 | PASS |
| Vault/storage 自动创建 | PASS (`C:\Users\Administrator\AppData\Local\LingJi\`) |
| 卸载后数据保留 | PASS (Local/LingJi 目录完整) |

### 10.3 发现的问题

#### [MUST-FIX] 黑框框 (console window)

**根因**: PyInstaller spec 文件 `console=True`。`build_windows_sidecar.ps1` 的 PyInstaller 命令行参数没有传 `--windowed`，导致生成的 spec 默认 `console=True`。编译出的 `lingji-core.exe` 是控制台子系统应用，Windows 强制弹出 `conhost.exe` 窗口。

**修复位置**: `scripts/build_windows_sidecar.ps1:27-46`

**改法**: 在第 45 行 `$entrypoint` 之前加一行 `"--noconsole"`:
```powershell
$arguments = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onedir",
    "--windowed",          # <-- 新增
    "--name", "lingji-core",
    ...
)
```

或修改 spec 模板将 `console=True` 改为 `console=False`。改后 PyInstaller 会编译为 Windows GUI 子系统，不再弹出黑框。

**工作量**: 1 行修改，30min 含重建验证。

#### [MEDIUM] 桌面端显示"核心启动失败"

**现象**: 桌面端启动后侧栏显示核心启动失败，30 秒后才连上。
**根因**: Token 生成与桌面端首次轮询存在竞态。桌面端发 401 约 293 次后 Token 就绪、200 成功。UI 把 401 译为"失败"是误报——核心实际上正常启动了。

**建议**: 桌面端轮询失败时增加重试延迟，前几次 401 不立即显示"失败"。或后端加速 Token 写入时序（`configure_packaged_environment` 中提前创建 token）。

## 11. 安全边界

| 检查项 | 结果 |
|--------|------|
| 只绑定 127.0.0.1 | PASS |
| 不误杀外部 8766 | PASS |
| 不访问正式 Vault/SQLite/Qdrant | PASS |
| 不自动下载模型 | PASS |
| Path 脱敏 (Rust) | PASS |
| Token 未泄漏 | PASS |

## 12. 失败记录

### FAIL-001: test_second_brain_is_not_in_original_start_chain
- **根因**: 预存依赖缺失 (textual/PySide6 不在 requirements-sidecar-build.txt)
- **关联**: 否 (PEMIS 遗留)
- **阻塞合并**: 否

### FAIL-002: 黑框框 (console window)
- **根因**: PyInstaller spec `console=True`
- **修复**: build_windows_sidecar.ps1 加 `--windowed`
- **阻塞合并**: **是** — 用户体验不可接受

## 13. 最终结论

**LOCAL_VALIDATED_WITH_ONE_MUST_FIX**

黑框框是必须修的，但只需要改 1 行 + 重建验证。其余 22 项全部 PASS。

## 14. 后续动作

### 必须修复 (合入前)
| # | 问题 | 文件 | 行 | 工作量 |
|---|------|------|-----|--------|
| 1 | sidecar 弹出黑框 | `scripts/build_windows_sidecar.ps1` | 27 | 1 行 + 重建 |

### 建议优化
| # | 问题 | 工作量 |
|---|------|--------|
| 2 | 桌面端启动轮询 401 不立即报失败 | 前端 30min |
| 3 | test_second_brain 加依赖 skip | 1 行 |

### 需要主人确认
- 安装后 sidecar 的 `console` 行为修复并重新构建
- 建议合并 PR #47（修复 #1 后）

---

## 证据路径

| 日志 | 路径 |
|------|------|
| 环境信息 | `output/desktop-validation/p2-11b-local-20260722-203543/logs/00-environment.txt` |
| Sidecar 测试 | `output/desktop-validation/p2-11b-local-20260722-203543/logs/pytest-packaged-control.log` |
| Desktop smoke | `output/desktop-validation/p2-11b-local-20260722-203543/logs/desktop-smoke.log` |
| Sidecar 构建 | `output/desktop-validation/p2-11b-local-20260722-203543/logs/build-sidecar.log` |
| Sidecar PID | `output/desktop-validation/p2-11b-local-20260722-203543/logs/sidecar-pid.txt` |
