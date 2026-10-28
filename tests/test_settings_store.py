import json
import tempfile
import unittest
from pathlib import Path
from settings_store import load_settings, save_settings


class SettingsStoreTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            self.assertEqual(load_settings(path), {"source": "", "destination": "", "roots": []})
            save_settings("/tmp/來源", "/tmp/整理", path)
            self.assertEqual(load_settings(path), {"source": "/tmp/來源", "destination": "/tmp/整理", "roots": []})

    def test_invalid_content_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text("not JSON", encoding="utf-8")
            self.assertEqual(load_settings(path), {"source": "", "destination": "", "roots": []})
