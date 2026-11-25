# Pulse Bridge for Tibber – Copyright 2026 Xander (Xander2980). Apache-2.0, see LICENSE.
"""Test setup: makes 'pulse_bridge.bridge_client' importable without a full Home Assistant install.

If Home Assistant is not installed, the few HA modules that the client (and const.py) import are
replaced by lightweight stubs. The package '__init__.py' (that needs the complete HA core) is skipped
by registering the package module manually.
"""
import dataclasses
import importlib.util
import pathlib
import sys
import types
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "custom_components" / "pulse_bridge"


class _StubMeta(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return f"{cls.__name__}.{name}"


@dataclasses.dataclass(frozen=True, kw_only=True)
class _EntityDescriptionStub:
    key: str
    name: Any = None
    icon: Any = None
    device_class: Any = None
    state_class: Any = None
    entity_category: Any = None
    entity_registry_enabled_default: bool = True
    native_unit_of_measurement: Any = None
    suggested_display_precision: Any = None
    translation_key: Any = None


class _StubModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if name.endswith("EntityDescription"):
            a_cls = dataclasses.dataclass(frozen=True, kw_only=True)(type(name, (_EntityDescriptionStub,), {}))
            setattr(self, name, a_cls)
            return a_cls
        a_cls = _StubMeta(name, (), {})
        setattr(self, name, a_cls)
        return a_cls


def _install_ha_stubs():
    if importlib.util.find_spec("homeassistant") is not None:
        return
    for mod_name in (
        "homeassistant",
        "homeassistant.const",
        "homeassistant.components",
        "homeassistant.components.sensor",
        "homeassistant.components.binary_sensor",
        "homeassistant.helpers",
        "homeassistant.helpers.event",
        "homeassistant.helpers.update_coordinator",
    ):
        sys.modules[mod_name] = _StubModule(mod_name)

    def async_call_later(hass, delay, action):
        return lambda: None

    sys.modules["homeassistant.helpers.event"].async_call_later = async_call_later


def _register_package():
    if "pulse_bridge" in sys.modules:
        return
    pkg = types.ModuleType("pulse_bridge")
    pkg.__path__ = [str(PKG_DIR)]
    sys.modules["pulse_bridge"] = pkg


_install_ha_stubs()
_register_package()
