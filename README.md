# <sub><img src="custom_components/pulse_bridge/brand/icon48.png" alt="" style="align:bottom;"></sub> Pulse Bridge for Tibber

Local Home Assistant integration for the **Tibber Pulse IR** and its **Pulse Bridge**. The integration reads the meter data (OBIS values) directly from the bridge in your LAN – via WebSocket push or HTTP polling – without the detour through the Tibber cloud or an additional MQTT proxy.

[![GitHub release][releasebadge]][release] [![Lint & Tests][testsbadge]][tests] [![Validate with hassfest][hassfestbadge]][hassfest] [![License][licensebadge]](LICENSE)

> [!IMPORTANT]
> This is an **unofficial** community project. It is not affiliated with, endorsed by or supported by Tibber. "Tibber" and "Tibber Pulse" are names of Tibber AS and are used here only to describe the hardware this integration works with.

> [!NOTE]
> Pulse Bridge for Tibber is an independent continuation of [marq24/ha-tibber-pulse-local](https://github.com/marq24/ha-tibber-pulse-local) (Apache License 2.0). See [NOTICE](NOTICE) for origin, copyright and the list of changes.

## Supported hardware

- **Tibber Pulse IR** reading head **with Pulse Bridge** (the extra device that is plugged into a power outlet).
- **Not supported:** Tibber Pulse P1, HAN or KM (used e.g. in Sweden, Norway or the Netherlands). These variants have no local bridge web server. For those you may want to look at [ha-tibber-pulse-mqtt](https://github.com/mrhedstrom/ha-tibber-pulse-mqtt).

Supported meter communication modes of the bridge:

- SML 1.04
- Plaintext
- IEC-62056.21
- Logarex
- Impressions (blinks / kWh) using the ambient sensor

The bridge also offers *AutoScanMode* and *Impressions using IR sensors*. These are not decoded yet – if your meter uses one of them, please open a [protocol report](https://github.com/Xander2980/pulse-bridge/issues/new?template=3-unsupported-type.yaml).

## Features

- Local push via the bridge WebSocket (default) or cyclic HTTP polling (interval from 2 s).
- Sensors for all common OBIS codes: import/export totals and tariffs (Wh and kWh), current power, power/voltage/current per phase, frequency and phase angles.
- Status sensors of the reading head (battery voltage, temperature, RSSI/LQI, radio TX power, uptime, packet counters) and of the bridge link (last seen, last data, average RSSI, packet delivery rate, LQI, availability).
- Re-authentication flow when the bridge password changes, reconfiguration of host/settings, repair issue if the bridge firmware no longer provides the data endpoints.
- Automatic detection of the bridge firmware (old `/data.json` and new `/node_data.json` endpoints) including firmware switches at runtime.
- Multiple Pulse reading heads on one bridge (one integration entry per node).

## Coexistence with `tibber_local`

Pulse Bridge for Tibber uses its own domain **`pulse_bridge`**. An existing installation of the original integration (`tibber_local`) is **not touched**: no configuration is migrated, no entity is renamed and both integrations can be installed side by side. Entities of the new integration get their own entity IDs (prefix `pulsebridge` by default) and unique IDs, so there are no collisions.

If you want to switch, add Pulse Bridge for Tibber, check the new entities and then remove the old integration yourself. Long-term statistics of the old entities are not transferred automatically – see [Troubleshooting & FAQ](docs/troubleshooting.md#can-i-keep-the-history-of-my-old-tibber_local-entities).

## Quick start

1. **Prepare the bridge:** the web frontend of the bridge must be enabled permanently (`webserver_force_enable`). Follow the [preparation guide](docs/preparation.md) – including the final checks.
2. **Install** via HACS (custom repository) or manually – see the [installation guide](docs/installation.md).
   
   [![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Xander2980&repository=pulse-bridge&category=integration)
3. **Restart** Home Assistant.
4. **Add the integration:**

   [![Open your Home Assistant instance and start setting up Pulse Bridge for Tibber.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=pulse_bridge)

   All options are explained in the [configuration guide](docs/configuration.md).

## Documentation

| Document | Content |
|---|---|
| [Preparation](docs/preparation.md) | Enable the bridge web frontend, verify pairing and data rate |
| [Installation](docs/installation.md) | HACS, manual installation, update, removal |
| [Configuration & usage](docs/configuration.md) | Setup options, entities, multiple nodes, reconfigure/re-auth |
| [Troubleshooting & FAQ](docs/troubleshooting.md) | Common problems, debug logging, frequently asked questions |
| [Bridge without Tibber contract](docs/non-tibber-customer.md) | Operating the bridge with your own MQTT broker |
| [Development](docs/development.md) | Project layout, tests, release process |
| [Changelog](CHANGELOG.md) | Version history |
| [Contributing](CONTRIBUTING.md) · [Support](SUPPORT.md) · [Security](SECURITY.md) | Project policies |

## Acknowledgements

- [marq24](https://github.com/marq24) and the contributors of [ha-tibber-pulse-local](https://github.com/marq24/ha-tibber-pulse-local), on whose work this project is based.
- [@spacemanspiff2007](https://github.com/spacemanspiff2007) for [SmlLib](https://github.com/spacemanspiff2007/SmlLib), which is used to decode the SML data.

## License

Apache License 2.0 – see [LICENSE](LICENSE) and [NOTICE](NOTICE).

[release]: https://github.com/Xander2980/pulse-bridge/releases/latest
[releasebadge]: https://img.shields.io/github/v/release/Xander2980/pulse-bridge?style=for-the-badge
[tests]: https://github.com/Xander2980/pulse-bridge/actions/workflows/tests.yaml
[testsbadge]: https://img.shields.io/github/actions/workflow/status/Xander2980/pulse-bridge/tests.yaml?branch=main&style=for-the-badge&label=tests
[hassfest]: https://github.com/Xander2980/pulse-bridge/actions/workflows/hassfest.yaml
[hassfestbadge]: https://img.shields.io/github/actions/workflow/status/Xander2980/pulse-bridge/hassfest.yaml?branch=main&style=for-the-badge&label=hassfest
[licensebadge]: https://img.shields.io/github/license/Xander2980/pulse-bridge?style=for-the-badge
