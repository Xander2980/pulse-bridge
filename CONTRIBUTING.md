# Contributing

Thanks for your interest in Pulse Bridge for Tibber. Bug reports, technical findings, documentation improvements and pull requests are welcome.

## Issues

Before opening an issue, please

- read the [documentation](README.md#documentation), especially [Troubleshooting & FAQ](docs/troubleshooting.md);
- search the [existing issues](https://github.com/Xander2980/pulse-bridge/issues?q=is%3Aissue) (open and closed);
- use the matching issue template and provide versions, a description of the problem and a **debug log** (see [how to enable debug logging](docs/troubleshooting.md#enable-debug-logging)).

Remove passwords, IP addresses, WiFi names and other private data from logs and screenshots.

Questions about usage are better placed in [GitHub Discussions](https://github.com/Xander2980/pulse-bridge/discussions) – see [SUPPORT.md](SUPPORT.md).

## Feature requests

Feature requests are evaluated by project scope and architecture, existing Home Assistant functionality, reliability, configuration complexity, backward compatibility and long-term maintenance effort. A request can therefore be declined even if it is technically possible.

As a design principle, the integration exposes the data the bridge provides. Interpretation of that data stays with Home Assistant or user automations where appropriate. For larger changes or new entities, please discuss the approach in an issue before you start.

## Pull requests

1. Fork the repository and create a branch from `main`.
2. Keep the change focused; do not mix refactoring with functional changes.
3. Run the checks locally (see [docs/development.md](docs/development.md)):
   ```bash
   pip install -r requirements_dev.txt
   ruff check --select F,E9,B,ASYNC --ignore F541 custom_components tests
   pytest -q
   ```
4. Add or update tests for changed behaviour and update the documentation and [CHANGELOG.md](CHANGELOG.md) (section *Unreleased*).
5. User-facing strings belong in `strings`/translations (`translations/en.json`, `de.json`, `pt.json`).

CI runs lint, tests, hassfest and HACS validation on every pull request.

## AI-assisted contributions

Using AI tools for code, research, translation or writing is allowed. You remain responsible for everything you submit: review and understand it, mark which parts were generated, verify technical claims and generated code, and respond to review feedback yourself.

## Conduct

Keep discussions respectful and focused on technical arguments. Issues that do not fit the scope of the project may be closed as *not planned*.

## Licensing of contributions

By submitting a contribution you confirm that you have the right to do so and that it is licensed under the [Apache License 2.0](LICENSE) of this project (Apache-2.0, section 5).
