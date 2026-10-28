import tempfile
import unittest
from pathlib import Path

from sortpilot import category_for, execute, plan, safe_filename, undo


class SortPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "in"
        self.destination = root / "organized"
        self.source.mkdir()

    def test_plan_does_not_move(self):
        file = self.source / "report.PDF"
        file.write_text("hello")
        moves = plan(self.source, self.destination)
        self.assertEqual(moves[0].category, "Documents")
        self.assertTrue(file.exists())
        self.assertFalse(self.destination.exists())

    def test_apply_and_undo(self):
        file = self.source / "data.csv"
        file.write_text("abc")
        batch, applied = execute(plan(self.source, self.destination), self.destination)
        self.assertEqual(len(applied), 1)
        self.assertFalse(file.exists())
        self.assertTrue((self.destination / "Spreadsheets" / "data.csv").exists())
        result = undo(self.destination, batch)
        self.assertEqual(len(result["restored"]), 1)
        self.assertEqual(file.read_text(), "abc")

    def test_collision_preserves_both_files(self):
        (self.source / "a.txt").write_text("new")
        existing = self.destination / "Documents" / "a.txt"
        existing.parent.mkdir(parents=True)
        existing.write_text("old")
        execute(plan(self.source, self.destination), self.destination)
        self.assertEqual(existing.read_text(), "old")
        self.assertEqual((existing.parent / "a (1).txt").read_text(), "new")

    def test_undo_refuses_modified_target(self):
        file = self.source / "x.txt"
        file.write_text("original")
        batch, _ = execute(plan(self.source, self.destination), self.destination)
        (self.destination / "Documents" / "x.txt").write_text("modified")
        result = undo(self.destination, batch)
        self.assertEqual(len(result["skipped"]), 1)
        self.assertFalse(file.exists())

    def test_symlink_skipped(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("private")
        try:
            (self.source / "link.txt").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        self.assertEqual(plan(self.source, self.destination), [])

    def test_nested_locations_rejected(self):
        with self.assertRaises(ValueError):
            plan(self.source, self.source / "sub")

    def test_filename_sanitizing(self):
        self.assertEqual(safe_filename("CON.txt"), "_CON.txt")
        self.assertEqual(category_for(Path("foo.unknown")), "Other")


if __name__ == "__main__":
    unittest.main()
