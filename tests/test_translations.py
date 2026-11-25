"""Every error key set in config_flow.py must exist in all translations, with the same placeholders."""
import json
import re
from pathlib import Path

COMP = Path(__file__).resolve().parent.parent / "custom_components" / "pulse_bridge"
LANGS = ("en", "de", "pt")


def _errors_used_in_flow():
    src = (COMP / "config_flow.py").read_text(encoding="utf-8")
    keys = set()
    for line in src.splitlines():
        if re.search(r"_errors\[[A-Z_]+\]\s*=", line):
            keys |= set(re.findall(r'"([a-z_]+)"', line))
    return keys


def _errors(lang):
    return json.loads((COMP / "translations" / f"{lang}.json").read_text(encoding="utf-8"))["config"]["error"]


def test_all_flow_errors_are_translated():
    used = _errors_used_in_flow()
    assert {"node_not_found", "node_prefilled"} <= used
    for lang in LANGS:
        missing = used - set(_errors(lang))
        assert not missing, f"{lang}.json misses {missing}"


def test_placeholders_match_english():
    en = _errors("en")
    for lang in LANGS:
        for key, text in _errors(lang).items():
            assert set(re.findall(r"{(\w+)}", text)) == set(re.findall(r"{(\w+)}", en[key])), f"{lang}:{key}"
