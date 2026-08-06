# PR #60 A-01 Codex 环境隔离修复报告

日期：2026-07-29  
分支：`feature/unified-ai-memory-connectors`  
来源验收报告：`acceptance/pr60-owner-255153c6`

## 1. 缺陷

主人真机验收发现：连接器 Core 使用：

```python
self.env = dict(env or os.environ)
```

当调用方明确传入 `env={}` 时，空映射被当作未提供参数，服务继承机器真实 `os.environ`。若机器设置了 `CODEX_HOME`，隔离测试可能错误读取或修改主人真实 Codex 配置。

原配置已经由验收程序从私有备份逐字节恢复，并验证 SHA256 一致。

## 2. 修复原则

- 不改变正常安装版的默认行为；
- `env=None` 仍表示继承当前进程环境；
- 显式传入任何映射，包括空映射，都必须严格使用该映射；
- 修复放在正式公共服务 `src.assistant_hub.governed.AiMemoryConnectorService`；
- Control API 继续通过 `src.assistant_hub` 使用公共服务；
- 不增加数据库、队列、端口、配置目录或写入路径；
- 不修改 MCP、记忆生命周期和第三方配置格式。

## 3. 实现

新增私有 `_ExplicitEnvironment`，仅用于区分：

```text
env=None  -> 继承 os.environ
env={}    -> 保持空环境，不继承 CODEX_HOME/PATH 等机器变量
env={...} -> 只使用调用方明确提供的环境
```

公共服务仍继承原 Connector Core，API 和返回结构不变。

## 4. 回归测试

`tests/test_ai_memory_connectors.py` 改为从正式公共入口 `src.assistant_hub` 导入服务，并新增：

```text
test_explicit_empty_environment_does_not_inherit_machine_codex_home
```

测试构造：

1. 在进程环境中设置一个模拟的真实 `CODEX_HOME`；
2. 在该目录写入主人配置哨兵内容；
3. 创建 `env={}` 的隔离连接器；
4. 执行 Codex 连接配置写入；
5. 验证写入只发生在隔离 Home；
6. 验证模拟主人配置内容完全不变；
7. 验证服务内部环境仍为空字典。

现有测试继续覆盖：

- Codex 配置保留；
- TOML 解析；
- 同名冲突拒绝；
- 精确确认；
- 备份与回滚；
- Claude 官方 CLI；
- WorkBuddy 预览脱敏；
- 未知连接器拒绝。

## 5. 验证门槛

必须在同一最终 Head 上通过：

```text
tests
P0 Windows Gate
Windows Desktop Release Baseline
```

并生成新的唯一 Windows Artifact。旧产品 Commit `255153c6` 和旧 Artifact `8720375948` 不得继续用于复验。

## 6. 真机复验要求

新的验收必须：

- 直接使用提供给主人的新 Artifact 文件，避免 GitHub Artifact HTTP 401；
- 重新运行连接器必测模块和完整 Python 套件；
- 验证真实 Codex 配置在隔离测试中没有变化；
- 完成之前因安装包不可用而未执行的 Desktop、MCP、导入、重启、Windows 重启和主人肉眼观察；
- 不得复用旧 FAIL 报告得出 PASS。

## 7. 当前状态

```text
A-01 FIX IMPLEMENTED: YES
REGRESSION TEST ADDED: YES
FULL CI: PENDING
NEW ARTIFACT: PENDING
OWNER RE-ACCEPTANCE: REQUIRED
MERGE ALLOWED: NO
```
