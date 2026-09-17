# 交接：嵌入式 Qdrant 客户端池（修 `already accessed by another instance`）

- 时间：2026-09-17
- 触发：`/api/observability/vectorize` 的 chunk 回填间歇整轮 `ERR`、`remaining` 长时间不动；
  状态接口把原因错报成「嵌入模型不可用」（`embedding.available=false`）。
- 结论：**同进程内两个 Qdrant 客户端工厂互抢文件锁**。与嵌入式模型无关。

## 现场证据

`/tmp/chunk_wire_err.log`（`observability_api.py` 的 `except` 里临时落的 traceback）：

```
File "src/control/observability_api.py", line 437, in observability_vectorize
File "src/retrieval/vector_backfill.py", line 49, in _shared_client
RuntimeError: Storage folder .../production/qdrant is already accessed by another instance
              of Qdrant client.
portalocker.exceptions.AlreadyLocked: [Errno 35] Resource temporarily unavailable
```

`lsof` 显示只有 **一个** 进程（`lingji-core.exe`）持有 `.lock`，所以不是跨进程冲突——是同一进程内
两个各自 `QdrantClient(path=...)` 的模块：

| 工厂 | 位置 | 是否共享 |
|---|---|---|
| 回填侧 | `vector_backfill._shared_client()` | 有进程内单例 |
| 网关侧 | `qdrant_provider.py` 的 `client` property（`bootstrap.py:97` 不传 `client=`） | **无，自建** |

**为什么同进程也会冲突**：嵌入式 Qdrant 靠 `<path>/.lock` 的 flock 独占。POSIX 的 flock 绑定的是
**open file description**，不是进程；`flock(2)` 明确写了同一进程换一个 fd 再加锁同样会被拒
（macOS 同）。最小复现已实测：

```python
a = QdrantClient(path=p)          # OK
b = QdrantClient(path=p)          # RuntimeError: ... already accessed by another instance
```

⚠️ **踩坑提醒**：复现时若不持有 `a` 的引用，它会被 GC 回收并释放锁，第二个客户端就「意外成功」——
调试时容易被误导。

## 改动

1. **新增 `src/retrieval/qdrant_client_pool.py`** —— 嵌入式客户端的**唯一创建入口**。
   - 键 = `expanduser` 规范化后的路径字符串（`str`/`Path`/结尾斜杠都归一到同一个键）。
   - **不主动关闭**：进程级共享资源，任何一方 `close()` 都会让其他持有者拿到死对象；
     只有 `close_all()`（测试/退出）才释放。
2. `src/retrieval/vector_backfill.py` —— `_shared_client()` / `close_shared_client()` 委派给池
   （**函数名保留**，`control/service.py`、`control/observability_api.py` 的调用点不用改）。
3. `src/retrieval/qdrant_provider.py` —— 嵌入式分支改走池，并把 `_owns_client` 置为 `False`
   （否则 provider 的 `close()` 会把共享客户端连带关掉）。
4. 新增 `tests/test_qdrant_client_pool.py` —— 4 条回归，覆盖两种加锁顺序 + 关闭不连带。

## 验证

```
pytest tests/test_qdrant_client_pool.py -q                      → 4 passed
pytest tests/test_qdrant_client_pool.py tests/test_qdrant_semantic_provider.py \
       tests/test_vector_backfill.py tests/test_chunk_vector_backfill.py \
       tests/test_observability_api.py tests/test_memory_retrieval.py \
       tests/test_vector_collection_migration.py -q             → 36 passed, 1 skipped
```

RED 已确认：把 `shared_embedded_client` 换回旧写法（各自 `QdrantClient(path=)`）后，
`test_provider_reuses_client_held_by_backfill` 精确复现 `QdrantUnavailableError`
（内层即上面那条 RuntimeError）。

## 待办（留给下一轮）

1. **需要重新打包 sidecar 才生效**。运行中的 `/Applications/灵机.app/Contents/Resources/lingji-core.exe`
   是 PyInstaller onedir 件（应用源码在 `base_library.zip` 内），源码改动不会热生效。
2. **`embedding.available=false` 是另一个 bug，不是锁**（本轮未改）：
   `_EmbeddingStatus.to_dict()` 里 `available = last_success_at and active_model and not last_error`，
   而 `control/service.py` 的实时状态每次**新建**一个 embedding provider、读完 status 立刻
   `close()` —— 计数器恒空，于是恒为 `False`。要让面板说真话，得复用进程级 provider，
   或在报 status 前做一次最小探活（建议加 TTL 缓存，别让每次轮询都打 Ollama）。
3. 修好后 `remaining` 应从当前缺口一次收敛到底；建议终验对照
   `/api/vector/coverage` 的 `live` 值 + `search_memory("薏仁")` 与 `/api/observability/recall` 一致。
