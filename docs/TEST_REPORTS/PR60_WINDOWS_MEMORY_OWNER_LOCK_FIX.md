# PR #60 Windows Memory Owner Lock 修复

## 问题

PR #72 首轮 Windows CI 证明：`msvcrt.locking` 获取 `memory-owner.lock` 后，同一进程之外再次以 `Path.read_text()` 打开该文件可能返回 `PermissionError: [Errno 13] Permission denied`。

锁的互斥功能本身有效，但把锁字节和诊断 JSON 放在同一个文件，导致 Windows 下无法在锁持有期间读取拥有者信息。

## 修复

运行时现在使用两个任务本地文件：

```text
runtime/memory-owner.lock
  只保存一个锁字节，由 msvcrt.locking / fcntl.flock 提供进程互斥。

runtime/memory-owner.json
  保存 owner、instance_id、workspace、pid、state、acquired_at、released_at。
  不参与互斥，可被 UI、日志和故障诊断安全读取。
```

释放锁后，诊断文件状态改为 `released`。进程异常结束时 OS 锁会自动释放；下一实例可重新获取锁并覆盖诊断元数据。

## 测试

`tests/test_memory_owner_lock.py` 覆盖：

- 第一个实例成功获取锁；
- 持锁期间诊断 JSON 可读取；
- 第二个实例在超时内被拒绝；
- 错误消息包含已有 owner/workspace 诊断；
- 释放后状态写为 `released`；
- 新实例可以重新接管；
- 重复 release 安全。

## 边界

- 文件只位于当前 DataRoot 的 `runtime` 目录；
- 不包含 Token、正文或私人路径清单；
- 不替代 DataRoot 启动契约；
- 不允许 Control API 创建第二个嵌入式 Qdrant 客户端；
- 真机 Windows 恢复时限仍需新的精确 Head Artifact 与 Day 0 验证。
