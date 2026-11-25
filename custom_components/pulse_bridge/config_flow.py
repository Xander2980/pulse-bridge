# Pulse Bridge for Tibber – based on marq24/ha-tibber-pulse-local (Apache-2.0).
# Modified by Xander (Xander2980), 2026: renamed and changed for Pulse Bridge for Tibber. See NOTICE.
import asyncio
import logging
from typing import Any

import probatio


from aiohttp import ClientError
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, SOURCE_RECONFIGURE
from homeassistant.const import (
    CONF_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_PASSWORD,
    CONF_MODE,
    CONF_DEVICE_ID, UnitOfTime
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector
from homeassistant.util import slugify

from . import PulseBridgeDataUpdateCoordinator
from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_HOST,
    DEFAULT_PWD,
    DEFAULT_USE_POLLING,
    DEFAULT_SCAN_INTERVAL,
    ENUM_IMPLEMENTATIONS,
    CONF_NODE_NUMBER,
    CONF_IGNORE_READING_ERRORS,
    CONF_USE_POLLING,
    CONF_OBIS_CODES,
    DEFAULT_NODE_NUMBER,
    CONFIG_VERSION,
    CONFIG_MINOR_VERSION,
    OBIS_DATA_KEY,
    UNKNOWN_SERIAL,
    MODE_3_SML_1_04,
)
from .bridge_client import PulseBridgeClient, BridgeAuthError, BridgeNotFoundError

_LOGGER = logging.getLogger(__name__)


def pulse_bridge_entries(hass: HomeAssistant):
    conf_hosts = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        a_host = entry.data[CONF_HOST]
        a_node = entry.data[CONF_NODE_NUMBER]

        if hasattr(entry, 'options'):
            if CONF_HOST in entry.options:
                a_host = entry.options[CONF_HOST]
            if CONF_NODE_NUMBER in entry.options:
                a_node = entry.options[CONF_NODE_NUMBER]

        # F-35: older entries might have stored the node number as float (3.0)
        try:
            a_node = int(a_node)
        except (TypeError, ValueError):
            pass
        conf_hosts.append(f"{a_node}@@{a_host}")
    return conf_hosts


def _host_in_configuration_exists(a_host: str, a_node, hass: HomeAssistant) -> bool:
    if f"{a_node}@@{a_host}" in pulse_bridge_entries(hass):
        return True
    return False

def _config_title_exists(a_title: str, hass: HomeAssistant) -> bool:
    return slugify(a_title) in [slugify(a_entry.title) for a_entry in hass.config_entries.async_entries(DOMAIN)]

class PulseBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = CONFIG_VERSION
    MINOR_VERSION = CONFIG_MINOR_VERSION

    def __init__(self):
        self._errors = {}
        self._default_name = DEFAULT_NAME
        self._default_host = DEFAULT_HOST
        self._default_pwd = DEFAULT_PWD
        self._default_use_polling = DEFAULT_USE_POLLING
        self._default_scan_interval = DEFAULT_SCAN_INTERVAL
        self._default_node_number = DEFAULT_NODE_NUMBER
        self._default_ignore_errors = False
        self._default_obis_codes = None
        self._node_device_id = None
        self._found_nodes = None

    async def _test_connection(self, host, pwd, node_num):
        self._errors = {}
        self._node_device_id = None
        self._found_nodes = None
        try:
            bridge = PulseBridgeClient(host=host, pwd=pwd, websession=async_get_clientsession(self.hass), node_num=node_num)
            try:
                # we MUST init the device_id
                await bridge.get_eui_for_node()
                if bridge.node_device_id is not None:
                    _LOGGER.debug(f"_test_connection(): Found device_id: {bridge.node_device_id} for node: {node_num}")
                    self._node_device_id = bridge.node_device_id
                    await bridge.detect_com_mode()
                    if bridge._com_mode in ENUM_IMPLEMENTATIONS:
                        self._con_mode = bridge._com_mode
                        return await self._test_data_available(bridge, host)
                    else:
                        self._errors[CONF_HOST] = "unknown_mode"
                elif bridge.node_id_list:
                    # the bridge answered, but has no node with the entered number - tell the user which ones exist
                    self._found_nodes = sorted(set(bridge.node_id_list))
                    self._errors[CONF_NODE_NUMBER] = "node_not_found"
                    _LOGGER.warning(f"_test_connection(): bridge at {host} has no node {node_num} - available nodes: {self._found_nodes}")
                else:
                    self._errors[CONF_HOST] = "unknown_device"

            except ValueError as val_err:
                self._errors[CONF_HOST] = "unknown_mode"
                _LOGGER.warning(f"_test_connection(): ValueError: {val_err}")

        except BridgeAuthError as exc:
            self._errors[CONF_PASSWORD] = "login_failed"
            _LOGGER.warning(f"_test_connection(): {exc}")
        except (OSError, ClientError, asyncio.TimeoutError, BridgeNotFoundError) as exc:
            self._errors[CONF_HOST] = "cannot_connect"
            _LOGGER.warning(f"_test_connection(): Could not connect to local Tibber Pulse Bridge at {host}, check host/ip address\n{type(exc).__name__} -> {exc}")
        return False

    async def _test_data_available(self, bridge: PulseBridgeClient, host: str) -> bool:
        try:
            await bridge.update_and_log()

            # unfortunately, there is no other parser than the PulseBridgeDataUpdateCoordinator,
            # so we must create a dummy one here, to be able to parse the serial data/number
            # from the found smart-meter
            coordinator = PulseBridgeDataUpdateCoordinator(self.hass, None)

            if len(bridge._obis_values.keys()) > 0:
                coordinator.data = {OBIS_DATA_KEY: bridge._obis_values}
                self._serial = coordinator.serial if coordinator.serial != UNKNOWN_SERIAL else self._node_device_id
                _LOGGER.info(f"_test_data_available(): Successfully connect to local Tibber Pulse Bridge at {host} - found serial: {self._serial}")
                if self._default_obis_codes is None:
                    self._default_obis_codes = list(bridge._obis_values.keys())
                return True
            else:
                await asyncio.sleep(2)
                await bridge.update_and_log()
                if len(bridge._obis_values.keys()) > 0:
                    coordinator.data = {OBIS_DATA_KEY: bridge._obis_values}
                    self._serial = coordinator.serial if coordinator.serial != UNKNOWN_SERIAL else self._node_device_id
                    _LOGGER.info(f"_test_data_available(): Successfully connect to local Tibber Pulse Bridge at {host} - found serial: {self._serial}")
                    if self._default_obis_codes is None:
                        self._default_obis_codes = list(bridge._obis_values.keys())
                    return True
                else:
                    _LOGGER.warning(f"_test_data_available(): No data from Tibber Pulse Bridge at {host}")
                    self._errors[CONF_HOST] = "no_data"
                    return False

        except BridgeAuthError as exc:
            self._errors[CONF_PASSWORD] = "login_failed"
            _LOGGER.warning(f"_test_data_available(): {exc}")
        except (OSError, ClientError, asyncio.TimeoutError, BridgeNotFoundError) as exc:
            self._errors[CONF_HOST] = "cannot_connect"
            _LOGGER.warning(f"_test_data_available(): Could not read data from local Tibber Pulse Bridge at {host}, check host/ip address\n{type(exc).__name__} -> {exc}")
        return False

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry_data = self._get_reconfigure_entry().data
        self._default_name = entry_data.get(CONF_NAME, DEFAULT_NAME)
        self._default_host = entry_data.get(CONF_HOST, DEFAULT_HOST)
        self._default_pwd = entry_data.get(CONF_PASSWORD, DEFAULT_PWD)
        self._default_use_polling = entry_data.get(CONF_USE_POLLING, DEFAULT_USE_POLLING)
        self._default_scan_interval = entry_data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self._default_node_number = entry_data.get(CONF_NODE_NUMBER, DEFAULT_NODE_NUMBER)
        self._default_ignore_errors = entry_data.get(CONF_IGNORE_READING_ERRORS, False)
        self._default_obis_codes = entry_data.get(CONF_OBIS_CODES, None)
        return await self.async_step_user()

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        # F-09: the bridge rejected the stored password
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            pwd = user_input[CONF_PASSWORD]
            bridge = PulseBridgeClient(host=entry.data[CONF_HOST], pwd=pwd,
                                       websession=async_get_clientsession(self.hass),
                                       node_num=int(entry.data.get(CONF_NODE_NUMBER, DEFAULT_NODE_NUMBER)),
                                       com_mode=int(entry.data.get(CONF_MODE, MODE_3_SML_1_04)))
            try:
                await bridge.get_eui_for_node()
                await bridge.update()
            except BridgeAuthError:
                errors[CONF_PASSWORD] = "login_failed"
            except (OSError, ClientError, asyncio.TimeoutError, BridgeNotFoundError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_PASSWORD: pwd})

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=probatio.Schema({
                probatio.Required(CONF_PASSWORD):
                    selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
            }),
            description_placeholders={"name": entry.title},
            errors=errors,
        )

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        self._errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST].lower()
            # make sure we just handle host/ip's - removing http/https
            if host.startswith("http://"):
                host = host.replace("http://", "")
            if host.startswith('https://'):
                host = host.replace("https://", "")

            name = user_input[CONF_NAME]
            pwd = user_input[CONF_PASSWORD]
            use_polling = user_input[CONF_USE_POLLING]
            # F-35: the NumberSelector delivers floats (3.0) - the bridge expects 'node_id=3'
            scan = int(user_input[CONF_SCAN_INTERVAL])
            node_num = int(user_input[CONF_NODE_NUMBER])
            ignore_errors = user_input[CONF_IGNORE_READING_ERRORS]

            if self.source != SOURCE_RECONFIGURE:
                # F-22: the previously set '_errors' were never shown (the flow was aborted directly)
                if _config_title_exists(name, self.hass) or _host_in_configuration_exists(host, node_num, self.hass):
                    return self.async_abort(reason="already_configured")

            if await self._test_connection(host, pwd, node_num):
                a_data = {CONF_NAME: name,
                          CONF_HOST: host,
                          CONF_PASSWORD: pwd,
                          CONF_USE_POLLING: use_polling,
                          CONF_SCAN_INTERVAL: scan,
                          CONF_NODE_NUMBER: node_num,
                          CONF_IGNORE_READING_ERRORS: ignore_errors,
                          CONF_ID: self._serial,
                          CONF_DEVICE_ID: self._node_device_id,
                          CONF_MODE: self._con_mode}

                # just store again the obis codes (that have been previously available in the config_entry)
                if self._default_obis_codes is not None:
                    a_data[CONF_OBIS_CODES] = self._default_obis_codes

                if self.source == SOURCE_RECONFIGURE:
                    return self.async_update_reload_and_abort(entry=self._get_reconfigure_entry(), data=a_data)
                else:
                    # F-22: without a unique_id '_abort_if_unique_id_configured()' was a no-op
                    if self._node_device_id is not None:
                        await self.async_set_unique_id(f"{DOMAIN}_{self._node_device_id}".lower())
                        self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=name, data=a_data)
            else:
                if self._found_nodes:
                    # only one node at the bridge: suggest it in the form
                    if len(self._found_nodes) == 1:
                        user_input = {**user_input, CONF_NODE_NUMBER: self._found_nodes[0]}
                elif self._node_device_id is not None:
                    _LOGGER.error(f"async_step_user(): Could not successfully read data from your Tibber Pulse Bridge at '{host}'. The specified host is fine - but the Integration could not detect the protocol - please enable the debug log to receive more details.")
                else:
                    _LOGGER.error(f"async_step_user(): Could not connect to Tibber Pulse Bridge at '{host}', check host ip address")
        else:
            user_input = {CONF_NAME: self._default_name,
                          CONF_HOST: self._default_host,
                          CONF_PASSWORD: self._default_pwd,
                          CONF_USE_POLLING: self._default_use_polling,
                          CONF_SCAN_INTERVAL: self._default_scan_interval,
                          CONF_NODE_NUMBER: self._default_node_number,
                          CONF_IGNORE_READING_ERRORS: self._default_ignore_errors}

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                probatio.Schema({
                    probatio.Required(CONF_NAME):
                        selector.TextSelector(),
                    probatio.Required(CONF_HOST):
                        selector.TextSelector(),
                    probatio.Required(CONF_PASSWORD):
                        selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
                    probatio.Required(CONF_USE_POLLING):
                        selector.BooleanSelector(),
                    probatio.Required(CONF_SCAN_INTERVAL):
                        selector.NumberSelector(selector.NumberSelectorConfig(
                            step=1,
                            min=2,
                            unit_of_measurement=UnitOfTime.SECONDS,
                            mode=selector.NumberSelectorMode.BOX)),
                    probatio.Required(CONF_NODE_NUMBER):
                        selector.NumberSelector(selector.NumberSelectorConfig(
                            step=1,
                            min=1,
                            max=25,
                            mode=selector.NumberSelectorMode.BOX)),
                    probatio.Required(CONF_IGNORE_READING_ERRORS):
                        selector.BooleanSelector(),
                }),
                user_input,
            ),
            description_placeholders={"repo": "https://github.com/Xander2980/pulse-bridge",
                                      "nodes": ", ".join(str(n) for n in (self._found_nodes or []))},
            last_step=True,
            errors=self._errors,
        )