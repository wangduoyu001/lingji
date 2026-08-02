# PR #60 可启动 Codex 命令解析修复

## 1. 背景

`PR60-MEMORY-QUALITY-TRIAL-4161807C` 在 Windows 真机上发现：

```text
shutil.which("codex") 返回 WindowsApps\codex.exe
该路径存在，但启动返回 Access is denied
PATH 后部可能仍存在可正常启动的 npm codex.cmd
```

上一轮修复已经能把这种情况诚实标记为 `client_launch_blocked`，但只报告失败仍不足以完成 Codex 接入。产品需要跳过不可启动的应用别名，继续寻找真正可运行的命令。

## 2. 实现

新增：

```text
src/assistant_hub/executable_resolution.py
```

解析器按确定性顺序检查：

1. `shutil.which` 返回的首选候选；
2. PATH 各目录中的 `codex` 与 PATHEXT 后缀；
3. `%APPDATA%\npm`；
4. `%LOCALAPPDATA%\npm`。

不执行递归磁盘搜索，不读取用户正文，不接受任意命令或 shell 片段。

每个候选先执行固定的 `--version` 探测：

- `PermissionError / Access is denied`：记录并继续下一个候选；
- 超时或非零退出：记录并继续；
- 成功：选为本次进程的可启动 Codex 命令；
- 全部失败：状态为 `launch_blocked`；
- 无候选：状态为 `not_found`。

Windows `.cmd/.bat` 通过固定 `cmd.exe /d /s /c` 调用，命令行由 `subprocess.list2cmdline` 从服务端固定参数生成。没有主人输入的 shell 内容。

## 3. 状态合同

Codex UI/API 新增并保留：

```text
client_available
client_launchable
client_command
client_resolution.state
client_resolution.candidate_count
client_resolution.attempts
```

规则：

- 路径存在但全部不可启动：`client_launch_blocked`；
- 第一个 WindowsApps 别名被拒绝、后续 npm shim 可启动：选择 npm shim，继续真实 `codex mcp list`；
- 只有选中的命令列出 `lingji-memory`，且配置与 MCP Runtime均有效，整体才为 `ready`。

## 4. 测试

新增：

```text
tests/test_executable_resolution.py
```

覆盖：

- WindowsApps alias 排在前面；
- alias Access Denied 后继续寻找 npm `codex.cmd`；
- `.cmd` 使用固定 COMSPEC 参数；
- 所有候选被拒绝时保持 `launch_blocked`；
- 不把“路径存在”当成“命令可启动”。

原有连接器测试继续覆盖：

- 配置存在但命令缺失；
- Access Denied 不显示 ready；
- `codex mcp list` 未列出 LingJi MCP；
- 真实注册验证成功后才 ready。

## 5. 安全边界

- 不扫描未知磁盘目录；
- 不读取 Codex历史、Session或配置正文；
- 不修改主人 PATH；
- 不下载或安装 Codex；
- 不通过 `shell=True` 执行任意字符串；
- 不削弱外部客户端配置授权和回滚合同。

## 6. 尚待证明

本报告提交时仍需精确 Head CI、Windows P0、正式 Release Artifact 和真机 Day 0 证明：

- WindowsApps alias 被跳过；
- 实际 npm/其他 PATH候选可启动；
- 真实 `codex mcp list` 列出 `lingji-memory`；
- 新安装包首次恢复在验收时限内；
- PR #60 继续保持 Draft。
