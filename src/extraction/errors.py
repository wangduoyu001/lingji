from __future__ import annotations


def safe_extraction_error(
    exc: Exception,
    *,
    message: str,
) -> str:
    """Return a stable external error summary without exposing exception details."""

    del exc
    return message
