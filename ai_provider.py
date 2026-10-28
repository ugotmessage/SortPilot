"""Bounded provider diagnostics, without sending document content."""
from __future__ import annotations
import json
import urllib.request
import urllib.error
from urllib.parse import urlsplit

PROVIDERS = {"off", "ollama", "openai", "compatible", "gemini"}
DEFAULT_URLS = {
    "ollama": "http://127.0.0.1:11434",
    "openai": "https://api.openai.com/v1",
    "compatible": "http://127.0.0.1:1234/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
}


def validate_ai(provider: str, url: str, model: str) -> None:
    if provider not in PROVIDERS:
        raise ValueError("Unsupported AI provider")
    if provider == "off":
        return
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Invalid provider URL")
    if parts.scheme == "http" and parts.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Remote AI services must use HTTPS")
    if not model.strip():
        raise ValueError("Model name is required")


def list_models(provider: str, url: str, api_key: str = "") -> list[str]:
    validate_ai(provider, url, "model-listing")
    if provider == "off":
        return []
    endpoint = url.rstrip("/") + ("/api/tags" if provider == "ollama" else "/models")
    headers = {"Accept": "application/json"}
    if provider != "ollama" and api_key:
        headers["Authorization"] = "Bearer " + api_key
    request = urllib.request.Request(endpoint, headers=headers)
    with urllib.request.urlopen(request, timeout=8) as response:
        if response.status != 200:
            raise RuntimeError("Model endpoint returned a non-success status")
        raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise RuntimeError("Model response exceeded size limit")
    data = json.loads(raw)
    records = data.get("models", []) if provider == "ollama" else data.get("data", [])
    return sorted({entry.get("name" if provider == "ollama" else "id")
                   for entry in records if isinstance(entry, dict)
                   and isinstance(entry.get("name" if provider == "ollama" else "id"), str)})
