from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class AuthState(str, Enum):
    NOT_CONFIGURED = "not_configured"
    CREDENTIAL_PRESENT = "credential_present"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    EXPIRED = "expired"
    PERMISSION_INSUFFICIENT = "permission_insufficient"
    INVALID = "invalid"
    ERROR = "error"


_ALLOWED_STATUS_FIELDS = {
    "provider",
    "auth_method",
    "state",
    "credential_present",
    "credential_valid",
    "permissions_ok",
    "account_bound",
    "last_verified_at",
    "expires_at",
    "last_error_code",
    "last_error_at",
}
_FORBIDDEN_VALUE = re.compile(
    r"(?:authorization\s*:|bearer\s+|basic\s+|\bsk-|\bgh[pousr]_|"
    r"access[_-]?token|refresh[_-]?token|api[_-]?key|cookie|session)",
    re.IGNORECASE,
)


class CredentialStoreError(RuntimeError):
    pass


class CredentialStore(Protocol):
    def get(self, provider: str) -> str | None: ...

    def set(self, provider: str, secret: str) -> None: ...

    def delete(self, provider: str) -> None: ...

    def exists(self, provider: str) -> bool: ...


class InMemoryCredentialStore:
    """CI-only fake backend. It must never be selected for a real desktop runtime."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def get(self, provider: str) -> str | None:
        return self._values.get(_provider(provider))

    def set(self, provider: str, secret: str) -> None:
        if not str(secret):
            raise CredentialStoreError("Credential must not be empty")
        self._values[_provider(provider)] = str(secret)

    def delete(self, provider: str) -> None:
        self._values.pop(_provider(provider), None)

    def exists(self, provider: str) -> bool:
        return self.get(provider) is not None


class UnavailableCredentialStore:
    """Safe runtime fallback where the platform has no supported system store."""

    def get(self, provider: str) -> str | None:
        return None

    def set(self, provider: str, secret: str) -> None:
        raise CredentialStoreError("System credential storage is unavailable")

    def delete(self, provider: str) -> None:
        return None

    def exists(self, provider: str) -> bool:
        return False


class MacOSKeychainCredentialStore:
    """macOS Keychain adapter using the system `security` command."""

    service_name = "com.lingji.credentials"

    def get(self, provider: str) -> str | None:
        result = self._run("find-generic-password", "-s", self.service_name, "-a", _provider(provider), "-w")
        return result.stdout.rstrip("\n") if result.returncode == 0 else None

    def set(self, provider: str, secret: str) -> None:
        if not str(secret):
            raise CredentialStoreError("Credential must not be empty")
        result = self._run(
            "add-generic-password", "-U", "-s", self.service_name, "-a", _provider(provider), "-w", str(secret)
        )
        if result.returncode:
            raise CredentialStoreError("Unable to save credential in macOS Keychain")

    def delete(self, provider: str) -> None:
        result = self._run("delete-generic-password", "-s", self.service_name, "-a", _provider(provider))
        if result.returncode not in {0, 44}:  # 44: item not found
            raise CredentialStoreError("Unable to remove credential from macOS Keychain")

    def exists(self, provider: str) -> bool:
        return self.get(provider) is not None

    @staticmethod
    def _run(*args: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(["security", *args], text=True, capture_output=True, check=False)
        except OSError as exc:
            raise CredentialStoreError("macOS Keychain is unavailable") from exc


class WindowsCredentialStore:
    """Windows Credential Manager adapter backed by CredRead/CredWrite."""

    prefix = "LingJi/"

    def get(self, provider: str) -> str | None:
        blob = self._read_blob(_provider(provider))
        if blob is None:
            return None
        return blob.decode("utf-16-le").rstrip("\0")

    def set(self, provider: str, secret: str) -> None:
        if not str(secret):
            raise CredentialStoreError("Credential must not be empty")
        import ctypes

        native = self._native()
        target = f"{self.prefix}{_provider(provider)}"
        target_buffer = ctypes.create_unicode_buffer(target)
        user_buffer = ctypes.create_unicode_buffer("LingJi")
        blob = (str(secret) + "\0").encode("utf-16-le")
        blob_buffer = ctypes.create_string_buffer(blob)
        credential = native.CREDENTIALW()
        credential.Type = native.CRED_TYPE_GENERIC
        credential.TargetName = ctypes.cast(target_buffer, ctypes.c_wchar_p)
        credential.CredentialBlobSize = len(blob)
        credential.CredentialBlob = ctypes.cast(blob_buffer, ctypes.POINTER(ctypes.c_byte))
        credential.Persist = native.CRED_PERSIST_LOCAL_MACHINE
        credential.UserName = ctypes.cast(user_buffer, ctypes.c_wchar_p)
        if not native.advapi32.CredWriteW(ctypes.byref(credential), 0):
            raise CredentialStoreError("Unable to save credential in Windows Credential Manager")

    def delete(self, provider: str) -> None:
        native = self._native()
        if not native.advapi32.CredDeleteW(f"{self.prefix}{_provider(provider)}", native.CRED_TYPE_GENERIC, 0):
            # ERROR_NOT_FOUND means the intended postcondition is already true.
            if native.ctypes.get_last_error() == 1168:
                return
            raise CredentialStoreError("Unable to remove credential from Windows Credential Manager")

    def exists(self, provider: str) -> bool:
        return self._read_blob(_provider(provider)) is not None

    @classmethod
    def _read_blob(cls, provider: str) -> bytes | None:
        native = cls._native()
        pointer = native.ctypes.POINTER(native.CREDENTIALW)()
        if not native.advapi32.CredReadW(f"{cls.prefix}{provider}", native.CRED_TYPE_GENERIC, 0, native.ctypes.byref(pointer)):
            if native.ctypes.get_last_error() == 1168:
                return None
            raise CredentialStoreError("Unable to read credential from Windows Credential Manager")
        try:
            credential = pointer.contents
            return bytes(credential.CredentialBlob[: credential.CredentialBlobSize])
        finally:
            native.advapi32.CredFree(pointer)

    @staticmethod
    def _native() -> Any:
        if os.name != "nt":
            raise CredentialStoreError("Windows Credential Manager is unavailable")
        import ctypes
        from ctypes import wintypes

        class CREDENTIALW(ctypes.Structure):
            _fields_ = [
                ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR), ("LastWritten", ctypes.c_byte * 8),
                ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
                ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
            ]

        return type("WindowsCredentialNative", (), {
            "ctypes": ctypes,
            "advapi32": ctypes.WinDLL("Advapi32.dll", use_last_error=True),
            "CREDENTIALW": CREDENTIALW,
            "CRED_TYPE_GENERIC": 1,
            "CRED_PERSIST_LOCAL_MACHINE": 2,
        })


def default_credential_store() -> CredentialStore:
    if sys.platform == "darwin":
        return MacOSKeychainCredentialStore()
    if os.name == "nt":
        return WindowsCredentialStore()
    return UnavailableCredentialStore()


class AuthStatusService:
    _DEFAULT_PROVIDERS = ("github", "codex", "local_control")

    def __init__(self, state_db: Any, credentials: CredentialStore) -> None:
        self.state_db = state_db
        self.credentials = credentials

    def refresh_presence(self, provider: str, *, auth_method: str) -> dict[str, Any]:
        present = self.credentials.exists(provider)
        return self.record(
            provider,
            auth_method=auth_method,
            state=AuthState.CREDENTIAL_PRESENT if present else AuthState.NOT_CONFIGURED,
            credential_present=present,
        )

    def record(
        self,
        provider: str,
        *,
        auth_method: str,
        state: AuthState | str,
        credential_present: bool,
        credential_valid: bool | None = None,
        permissions_ok: bool | None = None,
        account_bound: bool | None = None,
        last_verified_at: str | None = None,
        expires_at: str | None = None,
        last_error_code: str | None = None,
        last_error_at: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "provider": _provider(provider),
            "auth_method": _safe_scalar(auth_method, "auth_method"),
            "state": (state if isinstance(state, AuthState) else AuthState(str(state))).value,
            "credential_present": bool(credential_present),
            "credential_valid": _optional_bool(credential_valid),
            "permissions_ok": _optional_bool(permissions_ok),
            "account_bound": _optional_bool(account_bound),
            "last_verified_at": _safe_timestamp(last_verified_at),
            "expires_at": _safe_timestamp(expires_at),
            "last_error_code": _safe_scalar(last_error_code, "last_error_code", optional=True),
            "last_error_at": _safe_timestamp(last_error_at),
        }
        self.state_db.upsert_auth_status(payload)
        return payload

    def status(self, provider: str) -> dict[str, Any]:
        value = self.state_db.get_auth_status(_provider(provider))
        return value or self._not_configured(provider)

    def statuses(self) -> list[dict[str, Any]]:
        known = {str(item.get("provider")): item for item in self.state_db.list_auth_statuses()}
        return [known.get(provider, self._not_configured(provider)) for provider in self._DEFAULT_PROVIDERS] + [
            item for provider, item in known.items() if provider not in self._DEFAULT_PROVIDERS
        ]

    @staticmethod
    def _not_configured(provider: str) -> dict[str, Any]:
        return {
            "provider": _provider(provider), "auth_method": "unknown", "state": AuthState.NOT_CONFIGURED.value,
            "credential_present": False, "credential_valid": None, "permissions_ok": None,
            "account_bound": None, "last_verified_at": None, "expires_at": None,
            "last_error_code": None, "last_error_at": None,
        }


def export_auth_snapshot(
    state_db: Any,
    destination: Path | str,
    *,
    task_id: str,
    platform: str,
    untrusted: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a Git-safe allowlist snapshot. Untrusted input is deliberately ignored."""

    del untrusted
    providers: dict[str, dict[str, Any]] = {}
    blockers = 0
    for status in state_db.list_auth_statuses():
        state = str(status.get("state") or AuthState.NOT_CONFIGURED.value)
        if state in {AuthState.EXPIRED.value, AuthState.PERMISSION_INSUFFICIENT.value, AuthState.INVALID.value, AuthState.ERROR.value}:
            blockers += 1
        providers[str(status["provider"])] = {
            "credential_present": bool(status.get("credential_present")),
            "state": state,
            "permissions_ok": status.get("permissions_ok"),
        }
    payload = {
        "schema_version": 1,
        "task_id": _safe_scalar(task_id, "task_id"),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "platform": _safe_scalar(platform, "platform"),
        "providers": providers,
        "auth_blockers": blockers,
        "secret_export_count": 0,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if _FORBIDDEN_VALUE.search(encoded):
        raise CredentialStoreError("Auth snapshot contains forbidden secret-like content")
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(target)
    return payload


def _provider(value: str) -> str:
    return _safe_scalar(value, "provider")


def _safe_scalar(value: str | None, field: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    text = str(value or "").strip()
    if not text or len(text) > 120 or _FORBIDDEN_VALUE.search(text):
        raise ValueError(f"Unsafe {field}")
    return text


def _safe_timestamp(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or len(text) > 64 or _FORBIDDEN_VALUE.search(text):
        raise ValueError("Unsafe timestamp")
    return text


def _optional_bool(value: bool | None) -> bool | None:
    return None if value is None else bool(value)
