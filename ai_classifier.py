"""AI-first inbox classification. Suggested paths are restricted to existing approved folders.

No file is moved here. Text extraction is bounded; PDF needs optional pypdf.
"""
from __future__ import annotations
import json
import urllib.request
from pathlib import Path

from ai_provider import validate_ai
from archive_discovery import Root, validate_roots
from sortpilot import Move, safe_filename

TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".log", ".xml", ".html", ".py", ".rst"}
MAX_CONTENT = 6000
MAX_FILES = 100


def excerpt(path: Path) -> str:
    if path.suffix.lower() in TEXT_SUFFIXES:
        with path.open("rb") as stream:
            return stream.read(24000).decode("utf-8", errors="replace")[:MAX_CONTENT]
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return "[PDF content unavailable: install pypdf; filename only]"
        if path.stat().st_size > 15_000_000:
            return "[PDF too large; filename only]"
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages[:3])[:MAX_CONTENT]
    return "[Unsupported content format; filename only]"


def folders(inventory: dict) -> list[dict]:
    result = []
    for root in inventory["roots"]:
        base = Path(root["path"]).resolve()
        for record in root["folders"]:
            folder = (base / record["relative"]).resolve()
            if not folder.is_dir() or not (folder == base or base in folder.parents):
                continue
            result.append({"id": len(result), "category": root["category"],
                           "path": str(folder), "examples": record["examples"][:3]})
    return result


def call_model(ai: dict, api_key: str, prompt: dict) -> dict:
    provider, url, model = ai["provider"], ai["url"], ai["model"]
    validate_ai(provider, url, model)
    if provider == "off":
        raise ValueError("AI is disabled")
    if provider != "ollama" and not api_key:
        raise ValueError("API key required for remote model")
    system = ("Classify one file using only the supplied candidate folder IDs. "
              "Generate 1-8 short descriptive tags autonomously. Return strictly a JSON object "
              "with keys folder_id (integer or null), tags (array of strings), reason (string). "
              "If unsure, use null. Never invent a folder.")
    text = json.dumps(prompt, ensure_ascii=False)
    if provider == "ollama":
        endpoint = url.rstrip("/") + "/api/chat"
        body = {"model": model, "stream": False, "format": "json",
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": text}]}
    else:
        endpoint = url.rstrip("/") + "/chat/completions"
        body = {"model": model, "temperature": 0,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": text}]}
    headers = {"Content-Type": "application/json"}
    if provider != "ollama":
        headers["Authorization"] = "Bearer " + api_key
    request = urllib.request.Request(endpoint, data=json.dumps(body).encode(),
                                     headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=35) as response:
        raw = response.read(128_001)
        if len(raw) > 128_000:
            raise ValueError("AI response too large")
    response = json.loads(raw)
    content = (response["message"]["content"] if provider == "ollama"
               else response["choices"][0]["message"]["content"])
    if isinstance(content, dict):
        return content
    return json.loads(content)


def suggest_one(file: Path, options: list[dict], ai: dict, api_key: str,
                invoke=call_model) -> tuple[Move | None, dict]:
    # Candidate index is the only authority; model output is untrusted.
    answer = invoke(ai, api_key, {"filename": file.name, "content": excerpt(file),
                                  "folders": options[:200]})
    if not isinstance(answer, dict):
        raise ValueError("Invalid AI response")
    tags = answer.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    tags = [tag.strip()[:60] for tag in tags[:8]
            if isinstance(tag, str) and tag.strip()]
    choice = answer.get("folder_id")
    metadata = {"tags": tags, "reason": str(answer.get("reason", ""))[:240],
                "suggested_folder_id": choice}
    allowed = {entry["id"]: entry for entry in options[:200]}
    if type(choice) is not int or choice not in allowed:
        return None, metadata
    selected = allowed[choice]
    folder = Path(selected["path"])
    if not folder.is_dir() or folder.is_symlink():
        return None, metadata
    move = Move(str(file.resolve()), str(folder / safe_filename(file.name)),
                selected["category"], "AI suggestion; explicit review required")
    return move, metadata


def classify_inbox(source: Path, roots: list[Root], inventory: dict,
                   ai: dict, api_key: str, invoke=call_model) -> dict:
    validate_roots(source, roots)
    options = folders(inventory)
    source = source.resolve()
    moves, undecided, metadata, failures = [], [], {}, []
    candidates = [file for file in sorted(source.iterdir())
                  if file.is_file() and not file.is_symlink() and not file.name.startswith(".")]
    for file in candidates[:MAX_FILES]:
        try:
            move, info = suggest_one(file, options, ai, api_key, invoke)
            metadata[str(file)] = info
            if move:
                moves.append(move)
            else:
                undecided.append(str(file))
        except (Exception) as exc:
            # Failure remains visible and never schedules a move.
            failures.append({"file": str(file), "error": str(exc)[:200]})
            undecided.append(str(file))
    undecided.extend(str(file) for file in candidates[MAX_FILES:])
    return {"moves": moves, "undecided": undecided,
            "metadata": metadata, "failures": failures,
            "truncated": len(candidates) > MAX_FILES}
