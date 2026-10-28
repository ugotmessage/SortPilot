import tempfile
import unittest
from pathlib import Path
from archive_discovery import Root, discover
from ai_classifier import classify_inbox, suggest_one


class AIClassifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.source = base / "inbox"
        self.source.mkdir()
        self.archive = base / "archive"
        (self.archive / "Reports").mkdir(parents=True)
        self.file = self.source / "report.txt"
        self.file.write_text("Quarterly review", encoding="utf-8")
        self.roots = [Root("Work", str(self.archive))]
        self.inventory = discover(self.source, self.roots)
        self.ai = {"provider": "ollama", "url": "http://127.0.0.1:11434", "model": "fake"}

    def test_ai_tags_and_existing_destination(self):
        def fake(_ai, _key, payload):
            self.assertIn("Quarterly review", payload["content"])
            candidates = payload["folders"]
            folder = next(entry for entry in candidates if Path(entry["path"]).name == "Reports")
            return {"folder_id": folder["id"], "tags": ["work", "quarterly"], "reason": "report"}
        result = classify_inbox(self.source, self.roots, self.inventory, self.ai, "", fake)
        self.assertEqual(len(result["moves"]), 1)
        self.assertEqual(result["metadata"][str(self.file)]["tags"], ["work", "quarterly"])
        self.assertEqual(Path(result["moves"][0].target).parent.resolve(), (self.archive / "Reports").resolve())
        self.assertTrue(self.file.exists())

    def test_hallucinated_folder_rejected(self):
        result = classify_inbox(self.source, self.roots, self.inventory, self.ai, "",
                                lambda *_: {"folder_id": 99999, "tags": ["unknown"]})
        self.assertFalse(result["moves"])
        self.assertEqual(len(result["undecided"]), 1)

    def test_provider_failure_keeps_file(self):
        def fail(*_):
            raise RuntimeError("offline")
        result = classify_inbox(self.source, self.roots, self.inventory, self.ai, "", fail)
        self.assertFalse(result["moves"])
        self.assertEqual(len(result["failures"]), 1)
        self.assertTrue(self.file.exists())
