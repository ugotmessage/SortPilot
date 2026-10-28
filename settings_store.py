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
        return {"source": "", "destination": "", "roots": []}
    if not isinstance(data, dict):
        return {"source": "", "destination": ""}
    roots = data.get("roots", [])
    if not isinstance(roots, list):
        roots = []
    roots = [{"category": r["category"], "path": r["path"]} for r in roots
             if isinstance(r, dict) and isinstance(r.get("category"), str)
             and isinstance(r.get("path"), str)]
    # Existing single destination is not silently promoted into an approved archive root.
    return {"source": data.get("source", "") if isinstance(data.get("source"), str) else "",
            "destination": data.get("destination", "") if isinstance(data.get("destination"), str) else "",
            "roots": roots}


def save_settings(source: str, destination: str, path: Path | None = None) -> None:
    file = path or config_path()
    file.parent.mkdir(parents=True, exist_ok=True)
    temp = file.with_suffix(".tmp")
    temp.write_text(json.dumps({"source": source, "destination": destination},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(file)


def save_archive_settings(source: str, roots: list[dict], path: Path | None = None) -> None:
    file = path or config_path()
    file.parent.mkdir(parents=True, exist_ok=True)
    temp = file.with_suffix(".tmp")
    temp.write_text(json.dumps({"source": source, "destination": "",
                                "roots": roots}, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(file)
