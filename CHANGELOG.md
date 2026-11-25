# Changelog

All notable changes to this project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.2] – 2026-11-25

### Changed

- Setup: if the bridge reports exactly one Pulse and its node number was filled in, the message says so (“… the number has been filled in, please submit again”) instead of only listing the node numbers.
- Tests: every error message used by the setup form must exist in all translations with the same placeholders.

## [1.0.1] – 2026-11-25

### Fixed

- Setup: if the bridge has no Pulse under the entered node number, the form now names the node numbers the bridge reports and, if there is only one, fills it in. The previous message pointed to the `nodes.json` URL and did not say what was wrong.
- CI: the HACS action runs only in this repository.

## [1.0.0] – 2026-11-25

First release as the independent project **Pulse Bridge for Tibber**, based on [marq24/ha-tibber-pulse-local](https://github.com/marq24/ha-tibber-pulse-local) (commit `1fe05f9`, Apache-2.0). The version numbering starts anew and is not related to the version numbers of the original project.

### Changed – project identity

- New name *Pulse Bridge for Tibber*, repository `Xander2980/pulse-bridge`, Home Assistant domain `pulse_bridge` (was `tibber_local`), new icon and logo.
- Installs side by side with `tibber_local`; no migration of existing configuration or entities (see [installation](docs/installation.md#side-by-side-with-tibber_local)).
- Entity unique IDs use the prefix `pulse_bridge_uid_`, the default device name is `pulsebridge`.
- Release archive is `pulse_bridge.zip`.
- Code: classes renamed (`PulseBridgeClient`, `PulseBridgeDataUpdateCoordinator`, `PulseBridgeSensor`, …), module `tibber_client.py` → `bridge_client.py`. The legacy config-entry migration of the original project was removed because it can never run for the new domain.
- Documentation rewritten and split into `docs/`; donation and referral links removed; new CONTRIBUTING, SECURITY, SUPPORT and NOTICE files.

### Fixed – reliability (audit findings)

- WebSocket: connect timeout, frame size limit, masked pong, no sleep/retry chain inside the coordinator update, `CancelledError` is propagated.
- Parsing: tolerant header parser, plausibility filter for `total_increasing` energy totals, unitless values, rounding of scaled values.
- Authentication errors (HTTP 401/403) start the Home Assistant re-authentication flow; missing data endpoints (HTTP 404) create a repair issue.
- Timers and listeners are cleaned up on unload; a runtime switch of the bridge firmware is followed.
- Config flow: re-authentication step, unique ID per device with abort on duplicates, node number normalised to an integer, minimum polling interval 2 s.
- Binary sensor is `off` for `False`/`0`; entities no longer override their state.
- Translations without quoted placeholders (hassfest), `CONFIG_SCHEMA` added.

### Added

- Unit tests for the bridge client and a CI workflow for lint and tests.

[Unreleased]: https://github.com/Xander2980/pulse-bridge/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/Xander2980/pulse-bridge/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/Xander2980/pulse-bridge/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Xander2980/pulse-bridge/releases/tag/v1.0.0
