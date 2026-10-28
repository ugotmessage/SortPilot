# SortPilot

Local-first desktop file organizer for Windows and macOS.

## Current development status (archive discovery and scoped reorganization prototype)

- **One inbox, many archive roots.** In the desktop **設定** dialog, select one source folder, then add multiple existing archive folders and assign each a major category.
- A read-only bounded inventory discovers existing subfolders and samples filenames (not document contents) to suggest hierarchical destinations.
- Ambiguous or unmatched files remain unscheduled until the user opens **指定小分類…** to select an existing approved destination folder.
- Preview suggestions, review unresolved files in the dialog, optionally save exact filename routing preferences, skip selected rows, and explicitly confirm moves.
- One journal under SortPilot's local configuration directory supports undo across different archive roots.
- No AI provider or PDF content analysis is connected yet. Existing-folder token matching is only a conservative prototype and can be wrong.
- GitHub Actions runs tests on pushes and PRs; **building executable artifacts only happens with a manual workflow dispatch**.

## Two operating modes

- **Inbox mode**: one source folder, several approved archive roots; suggestions based on existing subfolder names.
- **Locked-folder reorganization mode**: pick one existing folder. Scan its top-level and nested files, including previously organized documents. Suggest moves only between existing subfolders inside the locked root. Ties and no-match files remain unchanged.
- Scoped mode validates all source and destination paths immediately before move confirmation; no proposed move is allowed outside the locked root. Symbolic links are not traversed.
- **Tags are AI-owned metadata**, not operator-maintained taxonomy. Future AI will generate and normalize multiple tags per document; users only change the suggested destination. The tagging engine has **not** been implemented yet.
- Neither mode autonomously creates, deletes or renames folders. Actual moves still need explicit confirmation.
- Scoped mode's manual unresolved-file routing UI is not implemented yet.

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

