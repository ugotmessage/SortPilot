"""Read-only discovery and conservative hierarchical routing.

No AI claims: matches existing folder names to filename tokens; ambiguous files
remain unassigned until reviewed. Does not inspect document content.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from sortpilot import Move, contained, safe_filename


@dataclass(frozen=True)
class Root:
    category: str
    path: str


def validate_roots(source: Path, roots: list[Root]) -> None:
    src = source.expanduser().resolve()
    if not src.is_dir():
        raise ValueError("Source folder does not exist")
    if not roots:
        raise ValueError("Please add at least one archive root")
    unique = set()
    for root in roots:
        if not root.category.strip() or not root.path.strip():
            raise ValueError("Category and path are required")
        dest = Path(root.path).expanduser().resolve()
        if not dest.is_dir():
            raise ValueError(f"Archive root does not exist: {dest}")
        if contained(src, dest) or contained(dest, src):
            raise ValueError("Source and archive roots cannot contain each other")
        if str(dest).casefold() in unique:
            raise ValueError("Archive root duplicated")
        unique.add(str(dest).casefold())


def discover(source: Path, roots: list[Root], max_dirs: int = 3000,
             max_files: int = 10000) -> dict:
    """Bounded read-only inventory. Symlink dirs are never traversed."""
    validate_roots(source, roots)
    results = []
    total_dirs = total_files = 0
    for root in roots:
        base = Path(root.path).expanduser().resolve()
        folders = [{"relative": ".", "examples": [], "files": 0}]
        pending = [base]
        while pending and total_dirs < max_dirs and total_files < max_files:
            folder = pending.pop(0)
            if folder.is_symlink():
                continue
            relative = folder.relative_to(base)
            entry = next((x for x in folders if x["relative"] == str(relative)), None)
            if entry is None:
                entry = {"relative": str(relative), "examples": [], "files": 0}
                folders.append(entry)
            total_dirs += 1
            try:
                children = sorted(folder.iterdir(), key=lambda x: x.name.casefold())
                for child in children:
                    if child.is_symlink() or child.name.startswith("."):
                        continue
                    if child.is_dir() and total_dirs + len(pending) < max_dirs:
                        pending.append(child)
                    elif child.is_file() and total_files < max_files:
                        total_files += 1
                        entry["files"] += 1
                        if len(entry["examples"]) < 5:
                            entry["examples"].append(child.name)
            except (OSError, PermissionError):
                entry["error"] = "unreadable"
        results.append({"category": root.category, "path": str(base), "folders": folders})
    return {"roots": results, "folders_scanned": total_dirs, "files_sampled": total_files,
            "truncated": bool(pending) or total_dirs >= max_dirs or total_files >= max_files}


def tokens(value: str) -> set[str]:
    return {x.casefold() for x in re.findall(r"[\w\u4e00-\u9fff]+", value) if len(x) >= 2}


def propose(source: Path, inventory: dict) -> tuple[list[Move], list[str]]:
    src = source.expanduser().resolve()
    suggestions: list[Move] = []
    unassigned: list[str] = []
    for file in sorted(src.iterdir(), key=lambda p: p.name.casefold()):
        if not file.is_file() or file.is_symlink() or file.name.startswith("."):
            continue
        name_tokens = tokens(file.stem)
        matches = []
        for root in inventory["roots"]:
            for folder in root["folders"]:
                relative = folder["relative"]
                labels = [] if relative == "." else list(Path(relative).parts)
                relevant = [tok for label in labels for tok in tokens(label)]
                score = sum(1 for tok in relevant if tok in name_tokens or tok in file.stem.casefold())
                # Existing samples help identify related files, but cannot decide a route alone.
                example_hits = sum(1 for example in folder["examples"] for tok in tokens(Path(example).stem)
                                   if tok in name_tokens)
                score += min(example_hits, 2)
                if score:
                    matches.append((score, len(labels), root, folder))
        matches.sort(key=lambda item: (-item[0], -item[1]))
        if not matches or (len(matches) > 1 and matches[0][0] == matches[1][0]):
            unassigned.append(str(file))
            continue
        score, _, root, folder = matches[0]
        target = Path(root["path"]) / ("" if folder["relative"] == "." else folder["relative"]) / safe_filename(file.name)
        suggestions.append(Move(str(file), str(target), root["category"],
                                f"existing archive match (score {score}); review required"))
    return suggestions, unassigned
