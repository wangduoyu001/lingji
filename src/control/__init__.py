from __future__ import annotations

from . import api as _api
from .api_contract import install_control_api_contract
from .runtime_settings import RuntimeSettingsStore

install_control_api_contract(_api)

__all__ = ["RuntimeSettingsStore", "LocalControlService"]


def __getattr__(name: str):
    if name == "LocalControlService":
        from .service import LocalControlService

        return LocalControlService
    raise AttributeError(name)
