import json
import tempfile
import unittest
from pathlib import Path
from settings_store import load_settings, save_settings, save_ai_settings, save_archive_settings


class SettingsStoreTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            self.assertEqual(load_settings(path), {"source": "", "destination": "", "roots": [], "ai": {"provider": "off", "url": "", "model": ""}})
            save_settings("/tmp/來源", "/tmp/整理", path)
            self.assertEqual(load_settings(path), {"source": "/tmp/來源", "destination": "/tmp/整理", "roots": [], "ai": {"provider": "off", "url": "", "model": ""}})

    def test_invalid_content_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text("not JSON", encoding="utf-8")
            self.assertEqual(load_settings(path), {"source": "", "destination": "", "roots": [], "ai": {"provider": "off", "url": "", "model": ""}})

    def test_ai_save_preserves_archives_and_not_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            save_archive_settings("/inbox", [{"category": "Reports", "path": "/reports"}], path)
            save_ai_settings("ollama", "http://127.0.0.1:11434", "qwen3", path)
            result = load_settings(path)
            self.assertEqual(result["roots"][0]["category"], "Reports")
            self.assertEqual(result["ai"]["model"], "qwen3")
            self.assertNotIn("api_key", path.read_text(encoding="utf-8"))
