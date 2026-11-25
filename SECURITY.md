# Security Policy

## Supported versions

Only the latest release of Pulse Bridge for Tibber receives security fixes.

| Version | Supported |
|---|---|
| 1.x (latest) | yes |
| older | no |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report them privately via GitHub: *Security → Report a vulnerability* in this repository ([direct link](https://github.com/Xander2980/pulse-bridge/security/advisories/new)). Include the affected version, a description, steps to reproduce and the possible impact.

You can expect an initial answer within 14 days. Please give the project reasonable time to provide a fix before disclosing details publicly.

## Scope and hints

- The integration talks to the Pulse Bridge only in your local network, using HTTP Basic Auth and an unencrypted WebSocket – this is what the bridge firmware offers. Keep the bridge in a trusted network segment.
- The bridge password is stored in the Home Assistant config entry. Never post it, your IP addresses or WiFi names in issues or logs.
- Vulnerabilities in the bridge firmware itself must be reported to the manufacturer, not to this project.
