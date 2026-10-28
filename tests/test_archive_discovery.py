import tempfile
import unittest
from pathlib import Path
from archive_discovery import Root, discover, propose, validate_roots


class ArchiveDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.inbox = base / "inbox"
        self.inbox.mkdir()
        self.research = base / "research"
        self.company = base / "company"
        (self.research / "台積電").mkdir(parents=True)
        (self.company / "合約").mkdir(parents=True)
        self.roots = [Root("投資", str(self.research)), Root("公司", str(self.company))]

    def test_multiple_roots_and_subfolder(self):
        (self.inbox / "台積電2026.pdf").write_text("x")
        (self.inbox / "random.bin").write_text("y")
        result = discover(self.inbox, self.roots)
        moves, unassigned = propose(self.inbox, result)
        self.assertEqual(len(moves), 1)
        self.assertIn("台積電", moves[0].target)
        self.assertEqual(len(unassigned), 1)
        self.assertTrue((self.inbox / "台積電2026.pdf").exists())

    def test_reject_source_nested_in_archive(self):
        with self.assertRaises(ValueError):
            validate_roots(self.research / "台積電", self.roots)

    def test_reject_duplicate_roots(self):
        with self.assertRaises(ValueError):
            validate_roots(self.inbox, self.roots + [Root("another", str(self.research))])

    def test_skip_symlink_directories(self):
        try:
            (self.research / "shortcut").symlink_to(self.company, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("No symlink permission")
        result = discover(self.inbox, self.roots)
        self.assertNotIn("shortcut", [x["relative"] for x in result["roots"][0]["folders"]])


if __name__ == "__main__":
    unittest.main()
