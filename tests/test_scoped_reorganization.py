import tempfile
import unittest
from pathlib import Path

from scoped_reorganization import propose_reorganization, validate_scoped_moves
from sortpilot import Move


class ScopedReorganizationTests(unittest.TestCase):
    def test_recommends_inside_tree_and_preserves_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "company"
            reports = root / "報告"
            reports.mkdir(parents=True)
            (root / "報告-2026.pdf").write_text("x")
            result = propose_reorganization(root)
            self.assertEqual(len(result["moves"]), 1)
            self.assertEqual(Path(result["moves"][0].target).parent.resolve(), reports.resolve())
            validate_scoped_moves(root, result["moves"])
            self.assertTrue((root / "報告-2026.pdf").exists())

    def test_reject_outside_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "company"
            root.mkdir()
            source = root / "a.pdf"
            source.write_text("x")
            external = Path(tmp) / "outside"
            external.mkdir()
            move = Move(str(source), str(external / "a.pdf"), "wrong", "test")
            with self.assertRaises(ValueError):
                validate_scoped_moves(root, [move])

    def test_reject_outside_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "company"
            root.mkdir()
            source = Path(tmp) / "outside.txt"
            source.write_text("x")
            with self.assertRaises(ValueError):
                validate_scoped_moves(root, [Move(str(source), str(root / "x.txt"), "x", "test")])

    def test_noop_is_not_suggested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "company"
            folder = root / "報告"
            folder.mkdir(parents=True)
            (folder / "報告2026.pdf").write_text("x")
            result = propose_reorganization(root)
            self.assertEqual(result["moves"], [])
