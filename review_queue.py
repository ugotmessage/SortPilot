"""Review queue helpers: safe existing-folder targets and explicit user corrections."""
from __future__ import annotations
import json
from pathlib import Path

from archive_discovery import Root
from settings_store import config_path
from sortpilot import Move, contained, safe_filename


def choices(roots: list[Root], inventory: dict) -> list[tuple[str, str]]:
    result = []
    for root in inventory["roots"]:
        for folder in root["folders"]:
            path = Path(root["path"]) / ("" if folder["relative"] == "." else folder["relative"])
            if path.is_dir() and not path.is_symlink():
                result.append((root["category"], str(path.resolve())))
    return result


def assign(file: str, category: str, folder: str, roots: list[Root]) -> Move:
    matches = [r for r in roots if r.category == category and
               contained(Path(folder).resolve(), Path(r.path).resolve())]
    if len(matches) != 1:
        raise ValueError("Selected folder is not inside exactly one approved archive root")
    target_dir = Path(folder).resolve()
    if not target_dir.is_dir() or target_dir.is_symlink():
        raise ValueError("Choose an existing archive directory")
    original = Path(file).resolve()
    if not original.is_file() or original.is_symlink():
        raise ValueError("Source is no longer a regular file")
    return Move(str(original), str(target_dir / safe_filename(original.name)),
                category, "manual review")


def rules_path() -> Path:
    return config_path().parent / "approved_routes.json"


def load_rules(path: Path | None = None) -> dict:
    file = path or rules_path()
    try:
        raw = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def remember(move: Move, roots: list[Root], path: Path | None = None) -> None:
    """Store exact filename preference only; no unapproved generalization."""
    target = Path(move.target).resolve().parent
    if not any(r.category == move.category and
               contained(target, Path(r.path).resolve()) for r in roots):
        raise ValueError("Target is no longer approved")
    file = path or rules_path()
    rules = load_rules(file)
    rules[Path(move.source).name.casefold()] = {
        "category": move.category, "folder": str(target)
    }
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_suffix(".tmp")
    tmp.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(file)


def recall(file: str, roots: list[Root], path: Path | None = None) -> Move | None:
    entry = load_rules(path).get(Path(file).name.casefold())
    if not isinstance(entry, dict):
        return None
    try:
        move = assign(file, entry["category"], entry["folder"], roots)
    except (KeyError, TypeError, ValueError, OSError):
        return None
    move.reason = "approved exact filename rule; review required"
    return move
