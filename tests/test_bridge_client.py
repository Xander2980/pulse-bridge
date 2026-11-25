# Pulse Bridge for Tibber – Copyright 2026 Xander (Xander2980). Apache-2.0, see LICENSE.
import asyncio
import json

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


# ---------------------------------------------------------------- config flow: report the node numbers of the bridge
class _FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload
        self.content_length = None
        self.content = self
        self._body = (payload.encode() if isinstance(payload, str) else json.dumps(payload).encode())

    async def read(self, n):
        chunk, self._body = self._body[:n], self._body[n:]
        return chunk

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    async def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, response):
        self._response = response

    def get(self, *args, **kwargs):
        return self._response


def test_unknown_node_reports_available_node_numbers():
    nodes = [{"node_id": 3, "eui": "AABBCCDDEEFF0011"}]
    bridge = PulseBridgeClient(host="127.0.0.1", pwd="test", websession=_FakeSession(_FakeResponse(200, nodes)), node_num=1)
    asyncio.run(bridge.get_eui_for_node())
    assert bridge.node_device_id is None
    assert bridge.node_id_list == [3]


def test_matching_node_sets_device_id():
    nodes = [{"node_id": 3, "eui": "AABBCCDDEEFF0011"}]
    bridge = PulseBridgeClient(host="127.0.0.1", pwd="test", websession=_FakeSession(_FakeResponse(200, nodes)), node_num=3)
    asyncio.run(bridge.get_eui_for_node())
    assert bridge.node_device_id == "aabbccddeeff0011"


# ---------------------------------------------------------------- reconfigure: truncated node_params.json (FW 2026_09)
def _node_params_text(count: int) -> str:
    params = [{"param_id": 27, "name": "meter_mode", "size": 1, "type": "uint8", "value": [3]}]
    params += [{"param_id": 100 + i, "name": f"param_{i}", "size": 1, "type": "uint8", "value": [i]} for i in range(count)]
    return json.dumps(params)


def test_tolerant_json_list_complete_and_truncated():
    text = _node_params_text(50)
    assert len(bridge_client.parse_json_list_tolerant(text)) == 51
    truncated = text[:1000]
    with pytest.raises(json.JSONDecodeError):
        json.loads(truncated)
    items = bridge_client.parse_json_list_tolerant(truncated)
    assert items[0]["name"] == "meter_mode"
    assert all(isinstance(item, dict) for item in items)
    assert 1 < len(items) < 51
    assert bridge_client.parse_json_list_tolerant("no json") == []
    assert bridge_client.parse_json_list_tolerant('{"a": 1}') == []


class _FakeTextResponse(_FakeResponse):
    async def text(self):
        return self._payload


def test_meter_mode_is_read_from_truncated_node_params():
    truncated = _node_params_text(200)[:7000]
    bridge = PulseBridgeClient(host="127.0.0.1", pwd="test", websession=_FakeSession(_FakeTextResponse(200, truncated)), node_num=3)
    asyncio.run(bridge.detect_com_mode_from_node_param27())
    assert bridge._com_mode == bridge_client.MODE_3_SML_1_04


# ---------------------------------------------------------------- reconfigure: fast retries with a time budget
def test_setup_read_uses_fast_retries_and_time_budget(monkeypatch):
    bridge = make_bridge()
    delays = []
    reads = []

    async def fake_sleep(delay):
        delays.append(delay)

    async def fake_read(mode, retry_count, log_payload=False, fw_redetected=False):
        reads.append(retry_count)
        # every read fails (e.g. CRC error) -> retry
        await bridge._check_for_retry_read(mode=mode, retry_count=retry_count)

    monkeypatch.setattr(bridge_client.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(bridge, "read_bridge_data", fake_read)
    asyncio.run(bridge.update_and_log())

    assert delays, "a failed read must be retried"
    assert all(bridge_client.SETUP_MIN_RETRY_DELAY <= d <= bridge_client.SETUP_MAX_RETRY_DELAY for d in delays)
    assert len(reads) <= bridge_client.SETUP_MAX_READ_RETRIES + 1
    # the flags are reset for the normal polling
    assert bridge._fast_retry is False
    assert bridge._read_deadline is None


def test_read_timeout_respects_time_budget():
    bridge = make_bridge()
    assert bridge._read_timeout() == 60.0
    bridge._read_deadline = bridge_client.time.monotonic() + 8.0
    assert bridge._read_timeout() <= 8.0
    bridge._read_deadline = bridge_client.time.monotonic() - 1.0
    assert bridge._read_timeout() == 5.0


# ---------------------------------------------------------------- SML: repair of telegrams with cleared bit 5 (CRC error)
def _sml_telegram() -> bytes:
    """A synthetic SML telegram (GetListResponse with import total + power) incl. a valid CRC."""
    entries = (
        bytes.fromhex("77" "070100010800ff" "01" "01" "621e" "52ff" "590000000000bc614e" "01")
        + bytes.fromhex("77" "070100100700ff" "01" "01" "621b" "5200" "55000001f4" "01")
    )
    get_list_res = bytes.fromhex("77" "01" "07010203040506" "01" "01" "72") + entries + bytes.fromhex("01" "01")
    message = bytes.fromhex("76" "0500000001" "6200" "6200" "72" "630701") + get_list_res + bytes.fromhex("630000" "00")
    body = b"\x1b\x1b\x1b\x1b\x01\x01\x01\x01" + message
    padding = (4 - len(body) % 4) % 4
    body += b"\x00" * padding + b"\x1b\x1b\x1b\x1b\x1a" + bytes([padding])
    crc = bridge_client.sml_crc_x25.get_crc(body)
    return body + bytes([crc >> 8, crc & 0xFF])


def _clear_bit5(telegram: bytes, count: int) -> bytes:
    data = bytearray(telegram)
    positions = [i for i in range(8, len(data) - 8) if data[i] == 0x62][:count]
    assert len(positions) == count
    for pos in positions:
        data[pos] &= ~0x20
    return bytes(data)


def test_sml_bit5_error_is_repaired():
    telegram = _sml_telegram()
    corrupted = _clear_bit5(telegram, 1)
    assert corrupted != telegram
    assert bridge_client.repair_sml_bit5_errors(corrupted) == telegram


def test_sml_two_bit5_errors_are_not_repaired():
    assert bridge_client.repair_sml_bit5_errors(_clear_bit5(_sml_telegram(), 2)) is None


def test_sml_other_errors_are_not_repaired():
    data = bytearray(_sml_telegram())
    data[30] ^= 0x01
    assert bridge_client.repair_sml_bit5_errors(bytes(data)) is None


def _read(bridge, payload):
    return asyncio.run(bridge.mode_03_read_sml(payload, retry_count=bridge.MAX_READ_RETRIES, log_payload=False))


def test_mode_03_rejects_repaired_telegram_without_known_totals():
    bridge = make_bridge()
    assert _read(bridge, _clear_bit5(_sml_telegram(), 1)) is False
    assert bridge._obis_values == {}


def test_mode_03_rejects_repaired_telegram_with_implausible_jump():
    bridge = make_bridge()
    assert _read(bridge, _sml_telegram()) is True
    known = bridge._obis_values[IMPORT_OBIS]
    bridge._obis_values[IMPORT_OBIS] = type("E", (), {"get_value": lambda self: 1234567.8 - 20_000})()
    assert _read(bridge, _clear_bit5(_sml_telegram(), 1)) is False
    assert known is not None


def test_mode_03_uses_repaired_telegram():
    bridge = make_bridge()
    assert _read(bridge, _sml_telegram()) is True
    ok = _read(bridge, _clear_bit5(_sml_telegram(), 1))
    assert ok is True
    assert bridge.crc_repaired_count == 1
    assert bridge._obis_values[IMPORT_OBIS].get_value() == pytest.approx(1234567.8)
    assert bridge._obis_values["0100100700ff"].get_value() == 500
