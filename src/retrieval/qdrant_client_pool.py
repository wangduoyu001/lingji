"""进程级嵌入式 Qdrant 客户端池：一个存储路径，只允许一个客户端。

为什么必须有这个模块
--------------------
嵌入式（local）模式靠 ``<path>/.lock`` 上的文件锁独占存储目录。POSIX 的 flock 绑定的是
**open file description**，不是进程——`flock(2)` 明确写着：同一进程用另一个 fd 再次加锁
同样会被拒（macOS 行为一致）。所以只要进程内存在两个各自 ``QdrantClient(path=...)``
的模块，后到的那个必然失败::

    RuntimeError: Storage folder <path> is already accessed by another instance
    of Qdrant client.

实测故障（2026-09-17）
--------------------
网关侧 ``QdrantSemanticProvider`` 自建客户端（``bootstrap.py`` 不传 ``client=``）后，
同进程 ``vector_backfill._shared_client()`` 再也拿不到锁：

- ``/api/observability/vectorize`` 的语义通道整段消失（``semantic_provider = None``），
  向量回填间歇整轮报错、``remaining`` 长时间不动；
- 状态接口把原因错报成「嵌入模型不可用」（实际是锁冲突，与模型无关）。

约定
----
- 本模块是嵌入式客户端的**唯一创建入口**，任何模块想连同一路径都必须经过它。
- **不主动关闭**：客户端是进程级共享资源，任何一方 ``close()`` 都会让其他持有者拿到
  死对象。仅在测试与进程退出时调用 :func:`close_all`。
- 按 ``expanduser`` + 路径规范化后的字符串做键，避免 ``str``/``Path``/结尾斜杠差异
  导致同一目录被当成两个键而重复建连。
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_CLIENTS: dict[str, Any] = {}


def _normalize(path: str | Path) -> str:
    """把路径统一成池的键：展开 ``~``、去掉结尾斜杠等冗余写法。"""
    return str(Path(path).expanduser())


def shared_embedded_client(path: str | Path) -> Any:
    """返回 ``path`` 对应的进程级共享客户端；首次调用时创建（幂等）。"""
    key = _normalize(path)
    with _LOCK:
        client = _CLIENTS.get(key)
        if client is not None:
            return client
        from qdrant_client import QdrantClient

        Path(key).mkdir(parents=True, exist_ok=True)
        client = QdrantClient(path=key)
        _CLIENTS[key] = client
        return client


def close_all() -> None:
    """释放全部共享客户端（仅测试与进程退出使用）。"""
    with _LOCK:
        for client in _CLIENTS.values():
            close = getattr(client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
        _CLIENTS.clear()


def pooled_paths() -> list[str]:
    """当前已被本进程持有的存储路径（诊断用）。"""
    with _LOCK:
        return list(_CLIENTS)


__all__ = ["shared_embedded_client", "close_all", "pooled_paths"]
