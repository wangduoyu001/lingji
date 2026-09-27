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

import logging
import threading
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_CLIENTS: dict[str, Any] = {}
_GUARDED_PATHS: set[str] = set()
_LOGGER = logging.getLogger(__name__)

# 混库守卫（PERF_RESOURCE_ROOT_CAUSE_20260927 B3）：qdrant-local 把集合注册表
# 持久化在 <path>/meta.json。若归档只删除了集合目录而没有注销注册，下次任何
# 进程打开同一路径时，qdrant-local 都会按注册表重建空目录——实测生产数据根的
# lingji_memory_acceptance 集合因此每次启动都被重建（2026-09-27 15:26:17 实锤）。
# 守卫规则刻意保守：只注销「非本工作区集合名 + lingji_memory_ 前缀 + 点数为 0」
# 的注册；有数据的外来集合只告警，绝不静默删除。
def _deregister_foreign_empty_collections(client: Any, own_collection: str) -> None:
    try:
        response = client.get_collections()
        items = getattr(response, "collections", response)
        names = {str(getattr(collection, "name", "")) for collection in items}
    except Exception:
        return
    for name in sorted(names):
        if not name or name == own_collection or not name.startswith("lingji_memory_"):
            continue
        try:
            count = int(client.count(collection_name=name, exact=True).count)
        except Exception:
            continue
        if count != 0:
            _LOGGER.warning(
                "embedded qdrant path hosts non-empty foreign collection %r; "
                "left untouched (mixed-collection guard)",
                name,
            )
            continue
        try:
            client.delete_collection(collection_name=name)
            _LOGGER.warning(
                "deregistered empty foreign collection %r from embedded qdrant "
                "storage (mixed-collection guard; registration was stale)",
                name,
            )
        except Exception:
            continue


def _normalize(path: str | Path) -> str:
    """把路径统一成池的键：展开 ``~``、去掉结尾斜杠等冗余写法。"""
    return str(Path(path).expanduser())


def shared_embedded_client(path: str | Path, *, own_collection: str | None = None) -> Any:
    """返回 ``path`` 对应的进程级共享客户端；首次调用时创建（幂等）。

    ``own_collection`` 由工作区感知的调用方传入（如语义 provider 传自己的集合名），
    使首次打开该路径时执行一次混库守卫：注销残留的、空的外来 ``lingji_memory_*``
    集合注册。
    """
    key = _normalize(path)
    with _LOCK:
        client = _CLIENTS.get(key)
        if client is not None:
            if own_collection and key not in _GUARDED_PATHS:
                _GUARDED_PATHS.add(key)
                _deregister_foreign_empty_collections(client, own_collection)
            return client
        from qdrant_client import QdrantClient

        Path(key).mkdir(parents=True, exist_ok=True)
        client = QdrantClient(path=key)
        _CLIENTS[key] = client
        if own_collection and key not in _GUARDED_PATHS:
            _GUARDED_PATHS.add(key)
            _deregister_foreign_empty_collections(client, own_collection)
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
        _GUARDED_PATHS.clear()


def pooled_paths() -> list[str]:
    """当前已被本进程持有的存储路径（诊断用）。"""
    with _LOCK:
        return list(_CLIENTS)


__all__ = ["shared_embedded_client", "close_all", "pooled_paths"]
