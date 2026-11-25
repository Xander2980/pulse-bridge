# Changelog

All notable changes to this project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.6] – 2026-11-25

### Fixed

- Read complete HTTP response bodies across network chunks while enforcing the size limit on all data and metadata endpoints.
- Report HTTP and decoding failures instead of treating cached meter readings as a successful update; preserve authentication and endpoint errors through retries.
- Keep HTTP fallback active when a classic-firmware WebSocket has never connected.
- Create status entities even if metadata is initially unavailable, allowing them to recover without reloading the integration.
- Pass the config entry explicitly to Home Assistant's data coordinator.

### Added

- Regression tests for streamed responses, failed reads, decoder fallback and metadata limits.
- Tests using real Home Assistant classes for coordinator availability, config/reauth flows, entity recovery and setup/unload, plus a dedicated Python 3.14 CI job.

## [1.0.5] – 2026-11-25

### Fixed

- Many SML telegrams were dropped with a CRC error (bridge delivers single bytes with bit 5 cleared, e.g. `b` → `B`). Such telegrams (up to two corrupted bytes) are now repaired; the repair is only used when the CRC matches again and the solution is unique. This also removes the delayed values caused by retries and the WebSocket fallback.
- Setup/reconfigure failed with "no data" when the first reads had CRC errors: the data test now runs for up to 30 s with up to 10 fast retries.

## [1.0.4] – 2026-11-25

### Fixed

- Reconfigure/setup took very long: a failed read (e.g. CRC error) was retried up to five times with 2.5–10 s pauses, twice in a row and without a time limit. Setup and reconfigure now retry after 1–2 s and stop after 15 s.
- Error `Unable to remove unknown job listener … start_watchdog` when the entry was reloaded (e.g. after reconfigure) after Home Assistant had started.

### Added

- Troubleshooting: values arrive with a delay (WebSocket ⛔ because a second integration uses the same node).

## [1.0.3] – 2026-11-25

### Fixed

- Reconfigure/setup failed with “please check the IP/host or the node number …” on bridges with firmware 2026_09: the bridge cuts `node_params.json` after 7000 characters, the invalid JSON was discarded and the meter mode (SML) was not detected. The complete parameters in front of the cut are now used.
- Removed the config entry update listener: reconfigure and re-authentication already reload the entry. Home Assistant 2026.12 no longer allows both.

### Changed

- Polling interval: minimum is now 1 second (only used with the polling procedure; the WebSocket mode already updates up to once per second).

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

[Unreleased]: https://github.com/Xander2980/pulse-bridge/compare/v1.0.6...HEAD
[1.0.6]: https://github.com/Xander2980/pulse-bridge/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/Xander2980/pulse-bridge/compare/v1.0.4...v1.0.5
[1.0.4]: https://github.com/Xander2980/pulse-bridge/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/Xander2980/pulse-bridge/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/Xander2980/pulse-bridge/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/Xander2980/pulse-bridge/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Xander2980/pulse-bridge/releases/tag/v1.0.0
