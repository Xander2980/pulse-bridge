# Configuration & usage

## Setup options

| Field | Description |
|---|---|
| Display name | Name of the device; also the prefix of the entity IDs (default `pulsebridge`). |
| IP or hostname | Address of the Pulse Bridge in your LAN (default `tibber-bridge`, the factory hostname of the bridge). A fixed IP address is recommended. |
| Bridge password | The password printed on the bridge below the QR code (pattern `XXXX-XXXX`, including the dash). |
| Use old polling procedure | Off (default): the bridge pushes data via WebSocket. On: data is requested cyclically via HTTP. Only use it if the WebSocket connection causes problems or another client already uses the WebSocket of this node. |
| Polling interval | Seconds between two HTTP requests (minimum 1 s, default 10 s). Only used with the polling procedure. |
| Node number (expert setting) | Node ID of the reading head on the bridge (default `1`). Check it on the *Pulse* page of the bridge web frontend. |
| Do not LOG errors or warnings while parsing data | Suppresses log messages about invalid data packets. |

During setup the integration checks that at least one OBIS value can be read. If no value is available, the setup fails with *Could not read any data from device* or *unknown mode* – see [troubleshooting](troubleshooting.md).

## Reconfigure and re-authenticate

- **Reconfigure:** *Settings → Devices & services → Pulse Bridge for Tibber → ⋮ → Reconfigure* changes host, password and the other options of an existing entry.
- **Re-authentication:** if the bridge rejects the stored password (HTTP 401/403), Home Assistant starts a re-authentication flow. Enter the current bridge password there.
- **Repair issue *data endpoints not found*:** created if the bridge answers HTTP 404 for its data endpoints even after a new firmware detection. Reload the integration; if the problem persists, open an issue.

## Entities

Only values that your meter actually delivers are created.

**Meter values (OBIS)**

| OBIS | Meaning |
|---|---|
| 1.8.0 – 1.8.4 | Import total and tariffs 1–4 (Wh and kWh) |
| 2.8.0 – 2.8.4 | Export total and tariffs 1–4 (Wh and kWh) |
| 16.7.0 | Current power |
| 36.7.0 / 56.7.0 / 76.7.0 | Power phase L1 / L2 / L3 |
| 32.7.0 / 52.7.0 / 72.7.0 | Voltage phase L1 / L2 / L3 |
| 31.7.0 / 51.7.0 / 71.7.0 | Current phase L1 / L2 / L3 |
| 14.7.0 | Grid frequency |
| 81.7.x | Phase angles |

Energy totals are `total_increasing` sensors and can be used in the Home Assistant energy dashboard. Implausible jumps of the totals (e.g. from corrupt packets) are filtered.

> [!NOTE]
> Many meters only deliver the current power (16.7.0) after the meter PIN has been entered at the meter ("extended data set"). Ask your meter operator for the PIN.

**Reading head and link status** (diagnostic, partly disabled by default)

Battery voltage, temperature, average RSSI and LQI, radio TX power, uptime, sent/received packet counters, corrupt/invalid reading counters, time in energy modes, receiver auto level, last seen, last data, packet delivery rate and availability of the node.

## Multiple Pulse reading heads on one bridge

Several reading heads can be paired with one bridge. Each one has its own **node number**. Add one integration entry per node with the same host and the matching *Node number*.

The bridge supports only **one WebSocket connection per node**. If more than one client reads the same node (for example this integration and the original `tibber_local`), enable *Use old polling procedure* for all but one of them.

## Using the data

- **Energy dashboard:** use *Import total* as grid consumption and *Export total* as return to grid.
- **Automations:** the current power sensor updates with every packet of the reading head (typically every 1–5 s), so it is suitable for surplus control. Use averaging (e.g. a statistics helper) if you need a calmer signal.
