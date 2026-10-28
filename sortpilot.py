"""SortPilot MVP: safe, cross-platform file organization CLI (standard library only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = {
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt"},
    "Spreadsheets": {".xlsx", ".xls", ".csv", ".ods"},
    "Presentations": {".ppt", ".pptx", ".key"},
    "Images": {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".svg"},
    "Videos": {".mp4", ".mov", ".avi", ".mkv"},
    "Audio": {".mp3", ".m4a", ".wav", ".flac"},
    "Archives": {".zip", ".7z", ".tar", ".gz", ".rar"},
    "Code": {".py", ".js", ".ts", ".json", ".html", ".css", ".rs", ".go"},
}
EXCLUDED = {".DS_Store", "Thumbs.db", "desktop.ini"}
RESERVED_WINDOWS = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}


@dataclass
class Move:
    source: str
    target: str
    category: str
    reason: str


def category_for(path: Path) -> str:
    for category, suffixes in CATEGORIES.items():
        if path.suffix.lower() in suffixes:
            return category
    return "Other"


def safe_filename(name: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    if not clean:
        clean = "untitled"
    if clean.split(".", 1)[0].upper() in RESERVED_WINDOWS:
        clean = "_" + clean
    return clean[:180]


def contained(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def plan(source: Path, destination: Path) -> list[Move]:
    source, destination = source.resolve(), destination.resolve()
    if source == destination or contained(destination, source) or contained(source, destination):
        raise ValueError("Source and destination must be separate, non-nested folders")
    if not source.is_dir():
        raise ValueError(f"Source folder does not exist: {source}")
    moves = []
    for item in sorted(source.iterdir(), key=lambda p: p.name.casefold()):
        if item.is_symlink() or not item.is_file() or item.name in EXCLUDED or item.name.startswith("."):
            continue
        category = category_for(item)
        target = destination / category / safe_filename(item.name)
        moves.append(Move(str(item), str(target), category, "extension rule"))
    return moves


def db_connect(destination: Path) -> sqlite3.Connection:
    destination.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(destination / ".sortpilot.sqlite3")
    db.execute("""CREATE TABLE IF NOT EXISTS journal (
        id TEXT PRIMARY KEY, batch TEXT NOT NULL, source TEXT NOT NULL,
        target TEXT NOT NULL, sha256 TEXT NOT NULL, moved_at TEXT NOT NULL,
        undone_at TEXT)""")
    db.commit()
    return db


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_target(target: Path) -> Path:
    if not target.exists():
        return target
    for number in range(1, 10001):
        candidate = target.with_name(f"{target.stem} ({number}){target.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("Too many filename collisions")


def execute(moves: list[Move], destination: Path) -> tuple[str, list[Move]]:
    batch = uuid.uuid4().hex
    performed = []
    with db_connect(destination) as db:
        for move in moves:
            src = Path(move.source)
            if src.is_symlink() or not src.is_file():
                continue
            target = unique_target(Path(move.target))
            target.parent.mkdir(parents=True, exist_ok=True)
            fingerprint = hash_file(src)
            # shutil.move can cross filesystems. Check the resulting target before journaling.
            shutil.move(str(src), str(target))
            db.execute("INSERT INTO journal VALUES (?, ?, ?, ?, ?, ?, NULL)",
                       (uuid.uuid4().hex, batch, str(src), str(target), fingerprint,
                        datetime.now(timezone.utc).isoformat()))
            db.commit()
            performed.append(Move(str(src), str(target), move.category, move.reason))
    return batch, performed


def undo(destination: Path, batch: str | None = None) -> dict:
    with db_connect(destination) as db:
        if batch is None:
            latest = db.execute("SELECT batch FROM journal WHERE undone_at IS NULL ORDER BY moved_at DESC LIMIT 1").fetchone()
            if latest is None:
                return {"restored": [], "skipped": [], "batch": None}
            batch = latest[0]
        rows = db.execute("SELECT id, source, target, sha256 FROM journal WHERE batch=? AND undone_at IS NULL ORDER BY moved_at DESC", (batch,)).fetchall()
        restored, skipped = [], []
        for row_id, source, target, fingerprint in rows:
            src, dst = Path(source), Path(target)
            if not dst.is_file() or dst.is_symlink() or src.exists() or hash_file(dst) != fingerprint:
                skipped.append({"target": target, "reason": "missing, modified, or source occupied"})
                continue
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(src))
            db.execute("UPDATE journal SET undone_at=? WHERE id=?", (datetime.now(timezone.utc).isoformat(), row_id))
            db.commit()
            restored.append(source)
    return {"batch": batch, "restored": restored, "skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SortPilot safe cross-platform file organizer")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "apply"):
        sub = commands.add_parser(command)
        sub.add_argument("source", type=Path)
        sub.add_argument("destination", type=Path)
        if command == "apply":
            sub.add_argument("--confirm", action="store_true", help="Required to move any files")
    sub = commands.add_parser("undo")
    sub.add_argument("destination", type=Path)
    sub.add_argument("--batch", default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "undo":
            result = undo(args.destination, args.batch)
        else:
            moves = plan(args.source, args.destination)
            if args.command == "apply":
                if not args.confirm:
                    parser.error("apply requires --confirm; use 'plan' to preview")
                batch, applied = execute(moves, args.destination)
                result = {"batch": batch, "moves": [asdict(m) for m in applied]}
            else:
                result = {"dry_run": True, "moves": [asdict(m) for m in moves]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
