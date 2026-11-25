# Pulse Bridge for Tibber – Copyright 2026 Xander (Xander2980). Apache-2.0, see LICENSE.
import asyncio

import pytest

from pulse_bridge import bridge_client
from pulse_bridge.bridge_client import PulseBridgeClient, WS_MAX_FRAME, ENERGY_JUMP_CONFIRMATIONS

IMPORT_OBIS = "0100010800ff"


class FakeEntry:
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value


def make_bridge() -> PulseBridgeClient:
    return PulseBridgeClient(host="127.0.0.1", pwd="test", websession=object(), node_num=1)


# ---------------------------------------------------------------- F-15: plaintext values
@pytest.mark.parametrize("raw, expected_value, expected_unit", [
    ("000123.456*kWh", 123456.0, "Wh"),
    ("1234*W", 1234, "W"),
    ("230.1*V", 230.1, "V"),
    ("ABC123", "ABC123", None),
])
def test_parse_plaintext_value(raw, expected_value, expected_unit):
    value, unit = PulseBridgeClient.parse_plaintext_value(raw)
    assert value == pytest.approx(expected_value) if isinstance(expected_value, float) else value == expected_value
    if expected_unit is None:
        assert unit is None
    else:
        assert unit == bridge_client.find_unit_int_from_string(expected_unit)
        assert unit is not None


# ---------------------------------------------------------------- F-13: websocket header
def test_header_parsing():
    assert PulseBridgeClient._ws_parse_header_string('<device:"ABCDEF" topic:"sml/data">') == ("sml/data", "abcdef")


def test_header_without_topic_and_device_does_not_raise():
    assert PulseBridgeClient._ws_parse_header_string("<foo bar>") == (None, None)
    assert PulseBridgeClient._ws_parse_header_bytes(b"\xff\xfe") == (None, None)


# ---------------------------------------------------------------- F-30
def test_gen_log_list_is_module_level():
    assert bridge_client.gen_log_list({}) == []


# ---------------------------------------------------------------- F-35
def test_node_number_float_is_converted():
    bridge = PulseBridgeClient(host="127.0.0.1", pwd="test", websession=object(), node_num=3.0)
    assert "node_id=3.0" not in bridge.url_data_classic
    assert bridge.url_data_classic.endswith("node_id=3")


# ---------------------------------------------------------------- F-14: energy totals
def test_energy_total_spike_is_ignored():
    bridge = make_bridge()
    bridge._set_obis_values({IMPORT_OBIS: FakeEntry(1_000_000)})
    # single implausible spike (+ 50 MWh) -> old value is kept
    bridge._set_obis_values({IMPORT_OBIS: FakeEntry(51_000_000)})
    assert bridge._obis_values[IMPORT_OBIS].value == 1_000_000
    # decreasing value -> old value is kept
    bridge._set_obis_values({IMPORT_OBIS: FakeEntry(999_000)})
    assert bridge._obis_values[IMPORT_OBIS].value == 1_000_000
    # normal increase is accepted
    bridge._set_obis_values({IMPORT_OBIS: FakeEntry(1_000_500)})
    assert bridge._obis_values[IMPORT_OBIS].value == 1_000_500


def test_energy_total_new_level_accepted_after_confirmations():
    bridge = make_bridge()
    bridge._set_obis_values({IMPORT_OBIS: FakeEntry(5_000_000)})
    # meter replaced: the new (lower) value is reported consistently
    for i in range(ENERGY_JUMP_CONFIRMATIONS):
        bridge._set_obis_values({IMPORT_OBIS: FakeEntry(100 + i)})
    assert bridge._obis_values[IMPORT_OBIS].value == 100 + ENERGY_JUMP_CONFIRMATIONS - 1


def test_non_energy_values_are_not_filtered():
    bridge = make_bridge()
    bridge._set_obis_values({"0100100700ff": FakeEntry(500)})
    bridge._set_obis_values({"0100100700ff": FakeEntry(-90_000_000)})
    assert bridge._obis_values["0100100700ff"].value == -90_000_000


# ---------------------------------------------------------------- F-04/F-05: self implemented websocket
async def _run_ws_against(server_frames: bytes):
    received = {}
    done = asyncio.Event()

    async def handler(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(server_frames)
        await writer.drain()
        try:
            received["client"] = await asyncio.wait_for(reader.read(1024), timeout=2)
        except asyncio.TimeoutError:
            received["client"] = b""
        done.set()
        writer.close()

    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    bridge = make_bridge()
    bridge.url_ws_host = f"127.0.0.1:{port}"
    buffers = []

    async def fake_handle_buffer(buffer):
        buffers.append(buffer)

    bridge.handle_buffer = fake_handle_buffer
    async with server:
        await asyncio.wait_for(bridge.ws_connect_2026_09(), timeout=5)
        await asyncio.wait_for(done.wait(), timeout=5)
    return bridge, received.get("client", b""), buffers


@pytest.mark.asyncio
async def test_pong_is_masked_and_text_frame_delivered():
    ping = bytes([0x89, 4]) + b"ping"
    data = bytes([0x82, 3]) + b"abc"
    close = bytes([0x88, 0])
    bridge, client_bytes, buffers = await _run_ws_against(ping + data + close)

    assert buffers == [b"abc"]
    assert client_bytes[:1] == b"\x8a"
    assert client_bytes[1] & 0x80, "client frames must be masked (RFC 6455)"
    length = client_bytes[1] & 0x7F
    mask = client_bytes[2:6]
    payload = bytes(b ^ mask[i % 4] for i, b in enumerate(client_bytes[6:6 + length]))
    assert payload == b"ping"
    assert bridge.ws_connected is False


@pytest.mark.asyncio
async def test_oversized_frame_is_rejected():
    huge = bytes([0x82, 127]) + (WS_MAX_FRAME * 100).to_bytes(8, "big")
    bridge, _, buffers = await _run_ws_against(huge)
    assert buffers == []
    assert bridge.ws_connected is False
    assert bridge.ws_writer is None
