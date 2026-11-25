# Troubleshooting & FAQ

## Three things that solve most problems

1. **Rotate the reading head** a few degrees anti-clockwise on the meter. The optical alignment has a strong effect on the data rate (see [preparation, part III](preparation.md#part-iii-check-last-seen--last-data-update-frequency)).
2. **Replace the batteries** of the reading head.
3. **Check the node number** (expert setting) – it must match the node shown on the *Pulse* page of the bridge.

## Setup fails

| Message | Cause and solution |
|---|---|
| *Login failed* | Wrong host or password. The password is printed on the bridge (pattern `XXXX-XXXX`, including the dash). |
| *Failed to connect* | The bridge is not reachable or its web frontend is not enabled permanently. Open `http://<bridge-ip>/` in a browser; if that does not work, follow the [preparation guide](preparation.md). |
| *Could not read any data from device* | The bridge answers but delivers no OBIS values. Check that a node is paired and sends data: `http://admin:<password>@<bridge-ip>/node_data.json?node_id=1` (old firmware: `/data.json?node_id=1`). |
| *unknown mode* | Wrong node number, or the meter uses a protocol that is not implemented yet – please open a [protocol report](https://github.com/Xander2980/pulse-bridge/issues/new?template=3-unsupported-type.yaml) with debug log. |
| *unknown device* | No device ID found for the node. Check `http://admin:<password>@<bridge-ip>/nodes.json`. |

## Log messages `Bytes missing...` or `CRC while parse data...`

Sometimes the bridge delivers an incomplete data packet. Such packets cannot be decoded by SmlLib and are skipped; the next packet is used. Single messages are harmless. Many messages usually mean a poor optical connection (rotate the reading head) or weak batteries. You can silence them with *Do not LOG errors or warnings while parsing data*.

## Values freeze or entities become unavailable

- Check *Last data* and *Packet delivery rate* of the node. A *Last data* value regularly above 5 s means the reading head has a poor connection to the meter.
- Check whether another client (e.g. a second integration) uses the WebSocket of the same node; enable polling for one of them.
- After a bridge firmware update the integration detects the new endpoints automatically. If the repair issue *data endpoints not found* appears, reload the integration.

## Values arrive with a delay

The Pulse sends a new meter reading every few seconds; with a working WebSocket the entities follow within about a second. The device model in *Settings → Devices* shows the state: **✅** = WebSocket connected, **⛔** = no WebSocket, the integration then only reads the data in the polling interval.

The most common reason for **⛔** is a second integration (e.g. the original `tibber_local`) that is connected to the same node – the bridge accepts only one WebSocket connection per node. Disable the other integration (or switch it to *Use old polling procedure*) and reload Pulse Bridge for Tibber. Nothing has to be changed at the meter.

## Enable debug logging

*Settings → Devices & services → Pulse Bridge for Tibber → ⋮ → Enable debug logging*, reproduce the problem, then *Disable debug logging* – Home Assistant offers the log file for download. Alternatively in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.pulse_bridge: debug
```

Remove passwords, IP addresses and other private data before you share logs.

## FAQ

### Does this integration need the Tibber cloud or a Tibber account?
No. All data is read locally from the bridge. The bridge itself still needs a valid MQTT configuration to stay in your WiFi – see [Bridge without Tibber contract](non-tibber-customer.md) if you are no longer a Tibber customer.

### Can I install it next to the original `tibber_local` integration?
Yes. It uses its own domain `pulse_bridge` and does not change the existing installation. Mind the one-WebSocket-per-node limit (see [configuration](configuration.md#multiple-pulse-reading-heads-on-one-bridge)).

### Can I keep the history of my old `tibber_local` entities?
Not automatically – the integration deliberately does not touch the old installation, and the new entities start their own history. To continue a statistic, remove the old integration first, then rename the entity ID of the new entity to the old entity ID in *Settings → Entities*; Home Assistant continues the long-term statistics under that ID.

### Does it work with Tibber Pulse P1, HAN or KM?
No, only with the Pulse IR plus bridge.

### Can the bridge be configured from Home Assistant?
No. The integration only reads data. Settings of the bridge are changed in its own web frontend.

### Why is the current power missing?
Many meters only send it after the meter PIN has been entered (extended data set).
