"""Scoped reorganization: read-only suggestions constrained to one archive tree.

A provisional filename-based engine, not AI. All moves require human approval.
"""
from __future__ import annotations

from pathlib import Path
from archive_discovery import Root, tokens
from sortpilot import Move, contained, safe_filename


def scope_path(root: Path, candidate: Path) -> bool:
    base = root.expanduser().resolve()
    path = candidate.expanduser().resolve()
    return contained(path, base)


def validate_scoped_moves(root: Path, moves: list[Move]) -> None:
    """Reject file escapes, no-op moves and symlink paths before execution."""
    base = root.expanduser().resolve()
    if not base.is_dir() or base.is_symlink():
        raise ValueError("Scope must be an existing real folder")
    for move in moves:
        src, dst = Path(move.source), Path(move.target)
        if src.is_symlink() or not src.is_file():
            raise ValueError("Source must be a regular file")
        if not scope_path(base, src) or not scope_path(base, dst):
            raise ValueError("Move escapes the locked folder")
        if src.resolve() == dst.resolve():
            raise ValueError("No-op move is not permitted")
        if not dst.parent.is_dir() or dst.parent.is_symlink():
            raise ValueError("Destination must be an existing real folder")
        # Prevent entering symlink directories through an intermediate path.
        relative = dst.parent.relative_to(base)
        current = base
        for segment in relative.parts:
            current = current / segment
            if current.is_symlink():
                raise ValueError("Symlink destination is not allowed")


def propose_reorganization(root: Path, max_dirs: int = 3000,
                           max_files: int = 10000) -> dict:
    """Walk the locked folder, including already classified documents.

    Only existing folders are candidates. Tie/weak matches are left untouched.
    """
    base = root.expanduser().resolve()
    if not base.is_dir() or base.is_symlink():
        raise ValueError("Scope must be an existing folder")
    folders = [base]
    documents: list[Path] = []
    index = 0
    truncated = False
    while index < len(folders):
        folder = folders[index]
        index += 1
        try:
            children = sorted(folder.iterdir(), key=lambda p: p.name.casefold())
        except OSError:
            continue
        for child in children:
            if child.is_symlink() or child.name.startswith("."):
                continue
            if child.is_dir():
                if len(folders) < max_dirs:
                    folders.append(child)
                else:
                    truncated = True
            elif child.is_file():
                if len(documents) < max_files:
                    documents.append(child)
                else:
                    truncated = True
    moves: list[Move] = []
    unresolved: list[str] = []
    unchanged = 0
    for file in documents:
        name = file.stem.casefold()
        name_tokens = tokens(file.stem)
        scores = []
        for folder in folders:
            if folder == base:
                continue
            label_tokens = {token for part in folder.relative_to(base).parts
                            for token in tokens(part)}
            score = sum(1 for token in label_tokens
                        if token in name_tokens or token in name)
            if score:
                scores.append((score, folder))
        scores.sort(key=lambda pair: -pair[0])
        if not scores or (len(scores) > 1 and scores[0][0] == scores[1][0]):
            unresolved.append(str(file))
            continue
        chosen = scores[0][1]
        if file.parent == chosen:
            unchanged += 1
            continue
        move = Move(str(file), str(chosen / safe_filename(file.name)),
                    chosen.relative_to(base).parts[0], "scoped folder name match; review required")
        validate_scoped_moves(base, [move])
        moves.append(move)
    return {"scope": str(base), "moves": moves, "unresolved": unresolved,
            "unchanged": unchanged, "folders_scanned": len(folders),
            "files_scanned": len(documents), "truncated": truncated}
