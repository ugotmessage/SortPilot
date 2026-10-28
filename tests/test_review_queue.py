import tempfile
import unittest
from pathlib import Path
from archive_discovery import Root, discover
from review_queue import assign, choices, recall, remember


class ReviewQueueTests(unittest.TestCase):
    def test_assign_and_recall(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inbox = base / "inbox"
            archive = base / "archive"
            sub = archive / "報表"
            inbox.mkdir()
            sub.mkdir(parents=True)
            item = inbox / "monthly.pdf"
            item.write_text("report")
            roots = [Root("公司", str(archive))]
            inventory = discover(inbox, roots)
            self.assertIn(("公司", str(sub.resolve())), choices(roots, inventory))
            move = assign(str(item), "公司", str(sub), roots)
            rulefile = base / "rules.json"
            remember(move, roots, rulefile)
            restored = recall(str(item), roots, rulefile)
            self.assertEqual(restored.target, move.target)
            self.assertEqual(item.read_text(), "report")

    def test_reject_outside_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            a, b = base / "a", base / "b"
            a.mkdir()
            b.mkdir()
            file = a / "x.txt"
            file.write_text("x")
            with self.assertRaises(ValueError):
                assign(str(file), "archive", str(a), [Root("archive", str(b))])
