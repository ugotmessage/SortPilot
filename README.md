# SortPilot

Local-first desktop file organizer for Windows and macOS.

## Current development status (archive discovery prototype)

- **One inbox, many archive roots.** In the desktop **設定** dialog, select one source folder, then add multiple existing archive folders and assign each a major category.
- A read-only bounded inventory discovers existing subfolders and samples filenames (not document contents) to suggest hierarchical destinations.
- Ambiguous or unmatched files remain unscheduled until the user opens **指定小分類…** to select an existing approved destination folder.
- Preview suggestions, review unresolved files in the dialog, optionally save exact filename routing preferences, skip selected rows, and explicitly confirm moves.
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

1. Enhance unresolved-file review with bulk choices, clearer category/folder navigation, and rule management.
2. Optional bounded content extraction and pluggable AI classification with privacy controls.
3. Persist user corrections and improve incremental index refresh.
4. Cross-platform signed installers only after manual approval.

