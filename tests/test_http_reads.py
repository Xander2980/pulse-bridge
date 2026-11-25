"""Regression tests for complete responses, read failures and decoder fallback."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest

from pulse_bridge.bridge_client import (
    MAX_RESPONSE_BYTES,
    MODE_3_SML_1_04,
    MODE_10_ImpressionsAmbient,
    MODE_99_PLAINTEXT,
    MODE_UNKNOWN,
    BridgeAuthError,
    BridgeNotFoundError,
    BridgeReadError,
    PulseBridgeClient,
    read_limited,
)


class Response:
    def __init__(self, body=b"", status=200, content_length=None):
        self.status = status
        self.content_length = content_length
        self.content = self
        self.body = body
        self.bytes_read = 0

    async def read(self, n):
        chunk, self.body = self.body[:n], self.body[n:]
        self.bytes_read += len(chunk)
        return chunk

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                SimpleNamespace(real_url="http://bridge/data.json"),
                (),
                status=self.status,
            )


def bridge_with(*responses, mode=MODE_3_SML_1_04):
    session = Mock()
    session.get.side_effect = responses
    bridge = PulseBridgeClient("bridge", "test", session, com_mode=mode)
    bridge.url_data = bridge.url_data_classic
    bridge.MAX_READ_RETRIES = 0
    return bridge


@pytest.mark.asyncio
async def test_reader_waits_for_remaining_network_chunks():
    protocol = Mock()
    protocol._reading_paused = False
    stream = aiohttp.StreamReader(protocol, limit=65536)
    stream.feed_data(b'{"kw":')
    task = asyncio.create_task(
        read_limited(
            SimpleNamespace(
                content=stream,
                content_length=None,
            )
        )
    )
    try:
        await asyncio.sleep(0)
        assert not task.done(), "the first network chunk is not the full response"
        stream.feed_data(b"1.25}")
        stream.feed_eof()
        assert await task == b'{"kw":1.25}'
    finally:
        if not task.done():
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task


@pytest.mark.asyncio
@pytest.mark.parametrize("length", [None, 8])
async def test_limit_accepts_exact_size(length):
    assert (
        await read_limited(Response(b"12345678", content_length=length), 8)
        == b"12345678"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("length", [None, 100])
async def test_limit_rejects_large_response_without_reading_entire_body(length):
    response = Response(b"x" * 100, content_length=length)
    with pytest.raises(ValueError, match="response too large"):
        await read_limited(response, 8)
    assert response.bytes_read <= 9


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [204, 500, 503])
async def test_http_failure_does_not_report_cached_values_as_success(status):
    bridge = bridge_with(Response(status=status))
    cached = {"old": object()}
    bridge._obis_values = cached
    with pytest.raises(aiohttp.ClientError):
        await bridge.update()
    assert bridge._obis_values is cached


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode,body",
    [
        (MODE_3_SML_1_04, b"invalid sml"),
        (MODE_99_PLAINTEXT, b"no meter data"),
        (MODE_10_ImpressionsAmbient, b'{"$type":"unknown"}'),
        (MODE_10_ImpressionsAmbient, b"invalid json"),
    ],
)
async def test_undecodable_data_fails_even_when_cache_exists(mode, body):
    bridge = bridge_with(Response(body), mode=mode)
    bridge._obis_values = {"old": object()}
    with pytest.raises(BridgeReadError):
        await bridge.update()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,error",
    [(401, BridgeAuthError), (403, BridgeAuthError), (404, BridgeNotFoundError)],
)
async def test_auth_and_endpoint_errors_survive_sml_retry(status, error, monkeypatch):
    bridge = bridge_with(Response(b"bad sml"), Response(status=status))
    bridge.MAX_READ_RETRIES = 1
    bridge._redetect_fw_after_404 = AsyncMock(return_value=False)
    monkeypatch.setattr("pulse_bridge.bridge_client.asyncio.sleep", AsyncMock())
    with pytest.raises(error):
        await bridge.update()


@pytest.mark.asyncio
async def test_successful_recursive_retry_is_not_reported_as_failure(monkeypatch):
    body = b'{"$type":"imp_data","kw":1.25,"kwh":2.5}'
    bridge = bridge_with(Response(b"bad sml"), Response(body))
    bridge.MAX_READ_RETRIES = 1
    original = bridge.read_bridge_data

    async def retry_as_impulses(mode, retry_count, **kwargs):
        return await original(MODE_10_ImpressionsAmbient, retry_count, **kwargs)

    monkeypatch.setattr("pulse_bridge.bridge_client.asyncio.sleep", AsyncMock())
    # Trigger the real recursive HTTP retry, switching only its decoder.
    bridge.read_bridge_data = retry_as_impulses
    await original(MODE_3_SML_1_04, 0)
    assert bridge._obis_values["0100100700ff"].get_value() == 1250


@pytest.mark.asyncio
async def test_mode_detection_continues_after_unsuccessful_probe():
    body = b'{"$type":"imp_data","kw":1.25}'
    bridge = bridge_with(Response(b"bad sml"), Response(body))
    bridge._com_mode = MODE_UNKNOWN
    await bridge._check_modes_internal(MODE_3_SML_1_04, MODE_10_ImpressionsAmbient)
    assert bridge._com_mode == MODE_10_ImpressionsAmbient


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method",
    ["_check_api_endpoint", "get_eui_for_node", "detect_com_mode_from_node_param27"],
)
async def test_metadata_endpoints_reject_oversized_bodies(method):
    response = Response(content_length=MAX_RESPONSE_BYTES + 1)
    bridge = bridge_with(response)
    if method == "_check_api_endpoint":
        await bridge._check_api_endpoint(bridge.url_test)
        assert bridge._test_data is None
    else:
        await getattr(bridge, method)()
        assert bridge.node_device_id is None
        if method == "detect_com_mode_from_node_param27":
            assert bridge._com_mode == MODE_UNKNOWN
    assert response.bytes_read == 0


@pytest.mark.asyncio
async def test_firmware_json_can_have_non_json_prefix_and_suffix():
    body = b"prefix\n" + json.dumps({"esp32_fw_v": "1794-test"}).encode() + b"\nsuffix"
    bridge = bridge_with(Response(body))
    await bridge.check_and_apply_fw_version()
    assert bridge.use_classic is False


@pytest.mark.asyncio
async def test_successful_plaintext_http_read_replaces_cached_values():
    body = b"1-0:1.8.0(123.45*kWh)\r\n1-0:16.7.0(42*W)\r\n!\r\n"
    bridge = bridge_with(Response(body), mode=MODE_99_PLAINTEXT)
    bridge._obis_values = {"old": object()}
    await bridge.read_bridge_data(MODE_99_PLAINTEXT, 0)
    assert "old" not in bridge._obis_values
    assert bridge._obis_values["0100010800ff"].get_value() == 123450
    assert bridge._obis_values["0100100700ff"].get_value() == 42
