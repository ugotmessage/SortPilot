# SortPilot

Local-first desktop file organizer for Windows and macOS.

## Current development status (archive discovery prototype)

- **One inbox, many archive roots.** In the desktop **設定** dialog, select one source folder, then add multiple existing archive folders and assign each a major category.
- A read-only bounded inventory discovers existing subfolders and samples filenames (not document contents) to suggest hierarchical destinations.
- Ambiguous or unmatched files are deliberately **not scheduled to move**; the status line shows their count. A full review queue for these files is pending.
- Preview the suggested destination paths, select rows to switch major category, skip rows, then explicitly confirm moves.
- One journal under SortPilot's local configuration directory supports undo across different archive roots.
- No AI provider or PDF content analysis is connected yet. Existing-folder token matching is only a conservative prototype and can be wrong.
- GitHub Actions runs tests on pushes and PRs; **building executable artifacts only happens with a manual workflow dispatch**.

## Run

```sh
python desktop.py
python -m unittest discover -s tests -v
```

Run with Python 3.10+ and Tkinter available. For early testing, create separate disposable test folders and do not use valuable personal data. Moves may fail halfway through (e.g. permissions/disk errors), and are not transactional across volumes.

## CLI (legacy single-destination workflow)

```sh
python sortpilot.py plan "/path/to/source" "/path/to/destination"
python sortpilot.py apply "/path/to/source" "/path/to/destination" --confirm
python sortpilot.py undo "/path/to/destination"
```

The CLI's older rule-based classification remains available separately from the desktop multi-root flow.

## Next steps

1. Full unresolved-file review queue with manual major/minor category assignment, target path validation and explicit mapping approval.
2. Optional bounded content extraction and pluggable AI classification with privacy controls.
3. Persist user corrections and improve incremental index refresh.
4. Cross-platform signed installers only after manual approval.

