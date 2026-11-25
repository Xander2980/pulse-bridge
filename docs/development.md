# Development

## Repository layout

| Path | Content |
|---|---|
| `custom_components/pulse_bridge/__init__.py` | Setup/unload, `PulseBridgeDataUpdateCoordinator`, WebSocket push and polling, re-auth and repair issue |
| `custom_components/pulse_bridge/bridge_client.py` | `PulseBridgeClient`: HTTP/WebSocket access to the bridge, SML/plaintext parsing |
| `custom_components/pulse_bridge/config_flow.py` | Config, options, reconfigure and re-authentication flow |
| `custom_components/pulse_bridge/sensor.py`, `binary_sensor.py` | Entities |
| `custom_components/pulse_bridge/const.py` | Domain, defaults, entity descriptions (OBIS codes) |
| `custom_components/pulse_bridge/translations/` | `en`, `de`, `pt` |
| `custom_components/pulse_bridge/brand/` | Icon and logo used by Home Assistant and HACS |
| `tests/` | Unit tests for the bridge client (no Home Assistant installation needed) |
| `.github/workflows/` | CI: tests, hassfest, HACS validation, release zip |

## Local setup

The lightweight client tests use Python 3.13 in CI. Tests against the declared minimum Home Assistant release (2026.9.0) use Python 3.14; that release requires Python 3.14.2 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements_dev.txt
```

## Checks

```bash
ruff check --select F,E9,B,ASYNC --ignore F541 custom_components tests
pytest -q
```

The CI workflow `tests.yaml` runs the same commands and additionally fails if `except BaseException` appears in `custom_components` (it would swallow `asyncio.CancelledError`). Without Home Assistant installed, `test_integration.py` is skipped and the client tests use lightweight HA stubs.

To run the complete suite against real Home Assistant classes, use a separate Python 3.14 environment:

```bash
python3.14 -m venv .venv-ha
source .venv-ha/bin/activate     # Windows: .venv-ha\Scripts\activate
pip install -r requirements_test_ha.txt
pytest -q
```

The dedicated `test-home-assistant` CI job runs this suite. It imports the actual integration package and checks HTTP fallback, failure/recovery availability, config and reauthentication flows, status entities with initially missing metadata, and setup/unload cleanup. Device communication is mocked; these tests do not require a bridge and do not replace a live-device test.

`hassfest.yaml` validates the integration with Home Assistant's hassfest, `hacs.yaml` runs the HACS action (only in the main repository, not in forks).

To test inside Home Assistant, copy `custom_components/pulse_bridge` into the `custom_components` folder of a test instance and enable debug logging (see [troubleshooting](troubleshooting.md#enable-debug-logging)).

## Releases

The project uses [Semantic Versioning](https://semver.org/).

1. Set `version` in `custom_components/pulse_bridge/manifest.json`.
2. Move the entries under *Unreleased* in [CHANGELOG.md](../CHANGELOG.md) to a new version section and update the compare links.
3. Commit, create the tag `vX.Y.Z` and push it.
4. Publish a GitHub release for the tag. The workflow `release.yaml` builds `pulse_bridge.zip` from `custom_components/pulse_bridge` and attaches it to the release; HACS installs this archive (`zip_release` in `hacs.json`).

## Origin

The code is based on [marq24/ha-tibber-pulse-local](https://github.com/marq24/ha-tibber-pulse-local) (Apache-2.0). Comments that reference upstream issues (`marq24/ha-tibber-pulse-local#…`) are kept on purpose: they document why certain workarounds exist. See [NOTICE](../NOTICE).
