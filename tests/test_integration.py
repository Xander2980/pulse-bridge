"""Integration regressions using real Home Assistant classes (no HA stubs).

Run with the dependencies from requirements_test_ha.txt on Python 3.14.
"""

from types import MappingProxyType
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from conftest import HA_INSTALLED

if not HA_INSTALLED:
    pytest.skip("requires requirements_test_ha.txt", allow_module_level=True)

from homeassistant.config_entries import ConfigEntry  # noqa: E402
from homeassistant.const import (  # noqa: E402
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_MODE,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady  # noqa: E402
from homeassistant.helpers import device_registry as dr, entity_registry as er, frame  # noqa: E402
from homeassistant.helpers.update_coordinator import UpdateFailed  # noqa: E402

from custom_components import pulse_bridge as integration  # noqa: E402
from custom_components.pulse_bridge import binary_sensor, config_flow, sensor  # noqa: E402
from custom_components.pulse_bridge.bridge_client import (  # noqa: E402
    BridgeAuthError,
    BridgeReadError,
)
from custom_components.pulse_bridge.const import (  # noqa: E402
    BINARY_SENSOR_TYPES,
    CONF_IGNORE_READING_ERRORS,
    CONF_NODE_NUMBER,
    CONF_USE_POLLING,
    DOMAIN,
    METRICS_KEY,
    MODE_3_SML_1_04,
    NODES_KEY,
    OBIS_DATA_KEY,
    SENSOR_TYPES,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def hass(tmp_path, monkeypatch):
    instance = HomeAssistant(str(tmp_path))
    instance.config_entries = Mock()
    instance.config_entries.async_entries.return_value = []
    instance.config_entries.async_forward_entry_setups = AsyncMock()
    instance.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    monkeypatch.setattr(config_flow, "async_get_clientsession", lambda hass: Mock())
    frame.async_setup(instance)
    dr.async_setup(instance)
    await dr.async_load(instance, load_empty=True)
    await er.async_load(instance, load_empty=True)
    yield instance
    await instance.async_stop()


def make_entry(host="bridge", device_id="aabb", entry_id=None):
    kwargs = {"entry_id": entry_id} if entry_id else {}
    return ConfigEntry(
        domain=DOMAIN,
        title="pulsebridge",
        version=2,
        minor_version=2,
        data={
            CONF_HOST: host,
            CONF_PASSWORD: "test",
            CONF_NAME: "pulsebridge",
            CONF_DEVICE_ID: device_id,
            CONF_MODE: MODE_3_SML_1_04,
            CONF_NODE_NUMBER: 1,
            CONF_USE_POLLING: False,
            CONF_SCAN_INTERVAL: 10,
            CONF_IGNORE_READING_ERRORS: False,
        },
        options={},
        source="user",
        unique_id=f"pulse_bridge_{device_id}",
        discovery_keys=MappingProxyType({}),
        subentries_data=None,
        **kwargs,
    )


@pytest.fixture
def entry():
    return make_entry()


@pytest_asyncio.fixture
async def coordinator(hass, entry, monkeypatch):
    monkeypatch.setattr(integration, "async_get_clientsession", lambda hass: Mock())
    result = integration.PulseBridgeDataUpdateCoordinator(hass, entry)
    result.data = {OBIS_DATA_KEY: {"old": object()}, NODES_KEY: {}, METRICS_KEY: {}}
    result.bridge._obis_values = result.data[OBIS_DATA_KEY]
    result.bridge.update = AsyncMock()
    yield result
    await result.async_shutdown()


async def test_classic_falls_back_until_first_websocket_message(coordinator):
    for _ in range(3):
        await coordinator.async_refresh()
    assert coordinator.bridge.update.await_count == 3
    assert coordinator.last_update_success


async def test_connected_websocket_does_not_poll(coordinator):
    coordinator.bridge.ws_connected = True
    await coordinator.async_refresh()
    coordinator.bridge.update.assert_not_awaited()


async def test_isolated_read_failures_keep_last_values(coordinator):
    entity = integration.PulseBridgeEntity(coordinator, SENSOR_TYPES[0])
    data = coordinator.data
    coordinator.bridge.update.side_effect = BridgeReadError("invalid meter data")
    for _ in range(integration.MAX_TOLERATED_READ_ERRORS):
        await coordinator.async_refresh()
        assert coordinator.last_update_success
        assert entity.available
        assert coordinator.data is data
    # a successful read resets the counter
    coordinator.bridge.update.side_effect = None
    await coordinator.async_refresh()
    coordinator.bridge.update.side_effect = BridgeReadError("invalid meter data")
    await coordinator.async_refresh()
    assert coordinator.last_update_success


async def test_read_failure_marks_entities_unavailable_and_recovers(coordinator):
    entity = integration.PulseBridgeEntity(coordinator, SENSOR_TYPES[0])
    coordinator.bridge.update.side_effect = BridgeReadError("invalid meter data")
    for _ in range(integration.MAX_TOLERATED_READ_ERRORS + 1):
        await coordinator.async_refresh()
    assert not coordinator.last_update_success
    assert isinstance(coordinator.last_exception, UpdateFailed)
    assert not entity.available
    coordinator.bridge.update.side_effect = None
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert entity.available


async def test_authentication_error_reaches_home_assistant(coordinator):
    coordinator.bridge.update.side_effect = BridgeAuthError("wrong password")
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_failed_refresh_requests_reauthentication(coordinator, monkeypatch):
    start_reauth = Mock()
    monkeypatch.setattr(
        coordinator.config_entry, "async_start_reauth_if_available", start_reauth
    )
    coordinator.bridge.update.side_effect = BridgeAuthError("wrong password")
    await coordinator.async_refresh()
    assert not coordinator.last_update_success
    assert isinstance(coordinator.last_exception, ConfigEntryAuthFailed)
    start_reauth.assert_called_once_with(coordinator.hass)


@pytest.mark.parametrize(
    "platform,descriptions",
    [
        (sensor, SENSOR_TYPES),
        (binary_sensor, BINARY_SENSOR_TYPES),
    ],
)
async def test_status_entities_recover_after_metadata_missing_at_setup(
    hass,
    entry,
    coordinator,
    platform,
    descriptions,
):
    hass.data[DOMAIN] = {entry.entry_id: coordinator}
    added = []
    await platform.async_setup_entry(hass, entry, added.extend)
    status_entities = [
        e for e in added if e.entity_description.tag.section in (NODES_KEY, METRICS_KEY)
    ]
    expected = [
        d for d in descriptions if d.tag and d.tag.section in (NODES_KEY, METRICS_KEY)
    ]
    assert {e.entity_description.key for e in status_entities} == {
        d.key for d in expected
    }
    assert status_entities
    assert all(not entity.available for entity in status_entities)
    coordinator.data[NODES_KEY] = {"node_id": 1}
    coordinator.data[METRICS_KEY] = {"node_status": {}}
    assert all(entity.available for entity in status_entities)


async def test_setup_and_unload_close_stream_and_cancel_timers(
    hass, entry, monkeypatch
):
    monkeypatch.setattr(integration, "async_get_clientsession", lambda hass: Mock())
    monkeypatch.setattr(
        integration.PulseBridgeDataUpdateCoordinator,
        "init_on_load",
        AsyncMock(return_value=True),
    )
    assert await integration.async_setup_entry(hass, entry)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, integration.PLATFORMS
    )
    timer = Mock()
    watchdog = Mock()
    coordinator._registry_timer_unsub = timer
    coordinator._watchdog = watchdog
    writer = Mock()
    writer.wait_closed = AsyncMock()
    coordinator.bridge.ws_writer = writer
    assert await integration.async_unload_entry(hass, entry)
    timer.assert_called_once()
    watchdog.assert_called_once()
    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited_once()
    assert entry.entry_id not in hass.data[DOMAIN]
    await coordinator.async_shutdown()


async def test_failed_platform_unload_keeps_runtime_data(hass, entry, coordinator):
    hass.data[DOMAIN] = {entry.entry_id: coordinator}
    hass.config_entries.async_unload_platforms.return_value = False
    assert not await integration.async_unload_entry(hass, entry)
    assert hass.data[DOMAIN][entry.entry_id] is coordinator
    assert not coordinator.bridge._terminating


async def test_config_flow_shows_connection_failure_for_invalid_meter_data(
    hass, entry, monkeypatch
):
    bridge = Mock()
    bridge.node_device_id = "aabb"
    bridge.get_eui_for_node = AsyncMock()
    bridge.detect_com_mode = AsyncMock()
    bridge._com_mode = MODE_3_SML_1_04
    bridge.update_and_log = AsyncMock(side_effect=BridgeReadError("invalid data"))
    monkeypatch.setattr(config_flow, "PulseBridgeClient", Mock(return_value=bridge))
    flow = config_flow.PulseBridgeConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}
    result = await flow.async_step_user(dict(entry.data))
    assert result["type"] == "form"
    assert result["errors"][CONF_HOST] == "cannot_connect"


async def test_config_flow_reports_wrong_password(hass, entry, monkeypatch):
    bridge = Mock()
    bridge.get_eui_for_node = AsyncMock(side_effect=BridgeAuthError("wrong password"))
    monkeypatch.setattr(config_flow, "PulseBridgeClient", Mock(return_value=bridge))
    flow = config_flow.PulseBridgeConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}
    result = await flow.async_step_user(dict(entry.data))
    assert result["errors"][CONF_PASSWORD] == "login_failed"


async def test_reauthentication_updates_only_password(hass, entry, monkeypatch):
    bridge = Mock()
    bridge.get_eui_for_node = AsyncMock()
    bridge.update = AsyncMock()
    monkeypatch.setattr(config_flow, "PulseBridgeClient", Mock(return_value=bridge))
    hass.config_entries.async_get_known_entry.return_value = entry
    flow = config_flow.PulseBridgeConfigFlow()
    flow.hass = hass
    flow.context = {"source": "reauth", "entry_id": entry.entry_id}
    result = await flow.async_step_reauth_confirm({CONF_PASSWORD: "new-password"})
    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
    updated = hass.config_entries.async_update_entry.call_args.kwargs["data"]
    assert updated == {**entry.data, CONF_PASSWORD: "new-password"}
    hass.config_entries.async_schedule_reload.assert_called_once_with(entry.entry_id)


async def test_reauthentication_rejects_invalid_data(hass, entry, monkeypatch):
    bridge = Mock()
    bridge.get_eui_for_node = AsyncMock()
    bridge.update = AsyncMock(side_effect=BridgeReadError("invalid data"))
    monkeypatch.setattr(config_flow, "PulseBridgeClient", Mock(return_value=bridge))
    hass.config_entries.async_get_known_entry.return_value = entry
    flow = config_flow.PulseBridgeConfigFlow()
    flow.hass = hass
    flow.context = {"source": "reauth", "entry_id": entry.entry_id}
    result = await flow.async_step_reauth_confirm({CONF_PASSWORD: "new-password"})
    assert result["type"] == "form"
    assert result["errors"]["base"] == "cannot_connect"
    hass.config_entries.async_update_entry.assert_not_called()


# --- device identity: an IP change must not create a new device -------------------------------


def _register(hass, *entries):
    known = {e.entry_id: e for e in entries}
    hass.config_entries.async_get_entry.side_effect = known.get


def _legacy_device(hass, entry, host, entity_keys=()):
    # identifier format up to 1.0.8: (DOMAIN, host, device_id)
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, host, entry.data[CONF_DEVICE_ID])},
        name="Pulse Bridge [local push]",
    )
    ent_reg = er.async_get(hass)
    for key in entity_keys:
        ent_reg.async_get_or_create(
            "sensor",
            DOMAIN,
            f"pulse_bridge_uid_{entry.data[CONF_DEVICE_ID]}_{key}",
            config_entry=entry,
            device_id=device.id,
        )
    return device


def _devices(hass, entry):
    return dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)


async def test_device_identifier_does_not_depend_on_host(hass, monkeypatch):
    monkeypatch.setattr(integration, "async_get_clientsession", lambda hass: Mock())
    first = make_entry(host="10.0.0.1")
    second = make_entry(host="10.0.0.2", entry_id=first.entry_id)
    infos = []
    for an_entry in (first, second):
        coordinator = integration.PulseBridgeDataUpdateCoordinator(hass, an_entry)
        infos.append(coordinator.get_device_info()["identifiers"])
        await coordinator.async_shutdown()
    assert infos[0] == infos[1] == {(DOMAIN, "aabb")}


async def test_ip_change_keeps_device_and_removes_orphans(hass):
    entry = make_entry(host="10.0.0.3")
    _register(hass, entry)
    _legacy_device(hass, entry, "10.0.0.1")
    _legacy_device(hass, entry, "10.0.0.2")
    current = _legacy_device(hass, entry, "10.0.0.3", ("0100010800ff", "available"))
    integration.async_migrate_device_identifiers(hass, entry)
    devices = _devices(hass, entry)
    assert [d.id for d in devices] == [current.id]
    assert devices[0].identifiers == {(DOMAIN, "aabb")}
    entities = er.async_entries_for_device(er.async_get(hass), current.id)
    assert {e.unique_id for e in entities} == {
        "pulse_bridge_uid_aabb_0100010800ff",
        "pulse_bridge_uid_aabb_available",
    }
    # restart / reload: migration is idempotent
    integration.async_migrate_device_identifiers(hass, entry)
    assert [d.id for d in _devices(hass, entry)] == [current.id]


async def test_device_with_entities_wins_over_host_match(hass):
    # the IP was changed again outside HA - entities still sit on the device of the old IP
    entry = make_entry(host="10.0.0.9")
    _register(hass, entry)
    with_entities = _legacy_device(hass, entry, "10.0.0.1", ("0100010800ff",))
    _legacy_device(hass, entry, "10.0.0.9")
    integration.async_migrate_device_identifiers(hass, entry)
    assert [d.id for d in _devices(hass, entry)] == [with_entities.id]


async def test_further_ip_changes_reuse_the_device(hass, monkeypatch):
    monkeypatch.setattr(integration, "async_get_clientsession", lambda hass: Mock())
    entry = make_entry(host="10.0.0.1")
    _register(hass, entry)
    device = _legacy_device(hass, entry, "10.0.0.1", ("0100010800ff",))
    integration.async_migrate_device_identifiers(hass, entry)
    for host in ("10.0.0.2", "10.0.0.3"):
        reconfigured = make_entry(host=host, entry_id=entry.entry_id)
        _register(hass, reconfigured)
        integration.async_migrate_device_identifiers(hass, reconfigured)
        coordinator = integration.PulseBridgeDataUpdateCoordinator(hass, reconfigured)
        identifiers = coordinator.get_device_info()["identifiers"]
        await coordinator.async_shutdown()
        assert dr.async_get(hass).async_get(device.id).identifiers == identifiers
        assert [d.id for d in _devices(hass, reconfigured)] == [device.id]


async def test_only_orphaned_devices_can_be_removed(hass):
    entry = make_entry()
    _register(hass, entry)
    current = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "aabb")}
    )
    orphan = _legacy_device(hass, entry, "10.0.0.1", ("0100010800ff",))
    assert not await integration.async_remove_config_entry_device(hass, entry, current)
    assert await integration.async_remove_config_entry_device(hass, entry, orphan)


async def test_multiple_bridges_keep_their_own_devices(hass):
    first = make_entry(host="10.0.0.1", device_id="aabb")
    second = make_entry(host="10.0.0.2", device_id="ccdd")
    _register(hass, first, second)
    dev_first = _legacy_device(hass, first, "10.0.0.1", ("0100010800ff",))
    dev_second = _legacy_device(hass, second, "10.0.0.2", ("0100010800ff",))
    integration.async_migrate_device_identifiers(hass, first)
    integration.async_migrate_device_identifiers(hass, second)
    assert [d.identifiers for d in _devices(hass, first)] == [{(DOMAIN, "aabb")}]
    assert [d.identifiers for d in _devices(hass, second)] == [{(DOMAIN, "ccdd")}]
    assert {d.id for d in _devices(hass, first) + _devices(hass, second)} == {
        dev_first.id,
        dev_second.id,
    }


async def test_unreachable_bridge_migrates_and_retries(hass, monkeypatch):
    monkeypatch.setattr(integration, "async_get_clientsession", lambda hass: Mock())
    entry = make_entry(host="10.0.0.2")
    _register(hass, entry)
    _legacy_device(hass, entry, "10.0.0.1")
    device = _legacy_device(hass, entry, "10.0.0.2", ("0100010800ff",))
    init = AsyncMock(return_value=False)
    monkeypatch.setattr(integration.PulseBridgeDataUpdateCoordinator, "init_on_load", init)
    with pytest.raises(ConfigEntryNotReady):
        await integration.async_setup_entry(hass, entry)
    assert [d.id for d in _devices(hass, entry)] == [device.id]
    # bridge reachable again -> setup succeeds with the same device
    init.return_value = True
    assert await integration.async_setup_entry(hass, entry)
    assert [d.id for d in _devices(hass, entry)] == [device.id]
    await integration.async_unload_entry(hass, entry)
