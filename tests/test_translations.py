"""Every language has every text."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from custom_components import homelab_wrapped

TRANSLATIONS = Path(homelab_wrapped.__file__).parent / "translations"


def keys(data: dict[str, Any], prefix: str = "") -> set[str]:
    found: set[str] = set()
    for key, value in data.items():
        found |= keys(value, f"{prefix}{key}.") if isinstance(value, dict) else {prefix + key}
    return found


def test_every_language_has_every_text() -> None:
    english = keys(json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8")))
    languages = sorted(TRANSLATIONS.glob("*.json"))
    assert [path.name for path in languages] == ["da.json", "en.json"]
    for path in languages:
        assert keys(json.loads(path.read_text(encoding="utf-8"))) == english, path.name
