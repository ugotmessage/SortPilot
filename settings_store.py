"""Local preferences storage for SortPilot (no network access)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def config_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "SortPilot" / "settings.json"


def load_settings(path: Path | None = None) -> dict[str, str]:
    file = path or config_path()
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"source": "", "destination": ""}
    if not isinstance(data, dict):
        return {"source": "", "destination": ""}
    return {key: value if isinstance(value, str) else ""
            for key in ("source", "destination") for value in [data.get(key)]}


def save_settings(source: str, destination: str, path: Path | None = None) -> None:
    file = path or config_path()
    file.parent.mkdir(parents=True, exist_ok=True)
    temp = file.with_suffix(".tmp")
    temp.write_text(json.dumps({"source": source, "destination": destination},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(file)
