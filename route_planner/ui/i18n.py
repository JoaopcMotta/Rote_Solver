from __future__ import annotations

import json
from pathlib import Path


class I18N:
    def __init__(self, lang: str = "pt_BR") -> None:
        self.lang = lang
        base = Path(__file__).resolve().parents[1] / "translations"
        file = base / f"{lang}.json"
        self.data = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}

    def t(self, key: str, default: str) -> str:
        return self.data.get(key, default)


i18n = I18N("pt_BR")
