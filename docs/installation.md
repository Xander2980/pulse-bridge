# Installation

Requirements:

- Home Assistant **2026.9.0** or newer.
- A Tibber Pulse IR with Pulse Bridge whose web frontend is enabled permanently – see the [preparation guide](preparation.md).

## Option 1: HACS (custom repository)

[![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Xander2980&repository=pulse-bridge&category=integration)

1. Install [HACS](https://hacs.xyz/) if you have not done so yet.
2. Click the button above, or in HACS open the three-dot menu → *Custom repositories* and add `https://github.com/Xander2980/pulse-bridge` with type **Integration**.
3. Search for **Pulse Bridge for Tibber** and download it. HACS installs the release archive `pulse_bridge.zip` of the selected version.
4. Restart Home Assistant.

## Option 2: Manual installation

1. Download `pulse_bridge.zip` from the [latest release](https://github.com/Xander2980/pulse-bridge/releases/latest).
2. Create the folder `custom_components/pulse_bridge/` in your Home Assistant configuration directory and extract the archive into it (the folder must directly contain `manifest.json`).
3. Restart Home Assistant.

Alternatively, copy the folder `custom_components/pulse_bridge/` from this repository to `custom_components/pulse_bridge/` in your configuration directory.

## Add the integration

[![Open your Home Assistant instance and start setting up Pulse Bridge for Tibber.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=pulse_bridge)

Or go to *Settings → Devices & services → Add integration* and search for **Pulse Bridge for Tibber**. The options are described in the [configuration guide](configuration.md).

## Update

- **HACS:** install the offered update and restart Home Assistant.
- **Manual:** replace the content of `custom_components/pulse_bridge/` with the new release and restart Home Assistant.

Check the [changelog](../CHANGELOG.md) before updating.

## Removal

1. *Settings → Devices & services → Pulse Bridge for Tibber →* delete every entry.
2. Remove the integration in HACS (or delete `custom_components/pulse_bridge/`).
3. Restart Home Assistant.

## Side by side with `tibber_local`

The integration uses the domain `pulse_bridge` and the folder `custom_components/pulse_bridge/`. An existing installation of the original `tibber_local` integration stays untouched – both can be installed at the same time. No configuration is imported from `tibber_local`; set up the bridge once more in Pulse Bridge for Tibber.

Note: both integrations then talk to the same bridge. The bridge accepts only **one WebSocket connection per node**, so while both are active, configure one of them with *Use old polling procedure* (see [configuration](configuration.md#multiple-pulse-reading-heads-on-one-bridge)).
