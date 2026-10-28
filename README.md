# SortPilot

Cross-platform, local-first file organizer for **Windows and macOS**. Initial milestone: **safe file handling and automation-ready CLI**. An AI classification provider and desktop UI are planned; **the current version does not use AI**.

## Current functionality

- Preview file organization by extension without changing anything (default)
- Move files only on explicit confirmation
- Protect existing files with numbered name collision handling
- Undo using SQLite journaling and SHA-256 validation
- Skip hidden files, folders and symlinks
- Output machine-readable JSON for a future GUI
- GitHub Actions tests on Linux, Windows and macOS, plus standalone Windows/macOS CLI artifacts

Requires Python 3.10+ for source execution; release artifacts bundle Python.

## Usage

```shell
python sortpilot.py plan "/path/to/Downloads" "/path/to/Sorted"
python sortpilot.py apply "/path/to/Downloads" "/path/to/Sorted" --confirm
python sortpilot.py undo "/path/to/Sorted"
python -m unittest discover -s tests -v
```

On Windows, use paths such as `"C:\\Users\\You\\Downloads"` and `"D:\\Sorted"`. The built executable is `sortpilot.exe` (Windows) or `sortpilot` (macOS). **It is currently a CLI executable, not a desktop app or installer.** Find it in the GitHub Actions run's Artifacts.

## Safety and limitations

No recursive scanning; top-level regular files only. Source and destination cannot be nested. The tool never deletes files. Undo skips any modified file or occupied original path, rather than overwriting. Use a backed-up test folder first; failed cross-volume moves or unexpected crashes can require manual reconciliation. Currently filename-extension rules only, with no content extraction, background monitoring, PDF understanding, cloud integrations, GUI, signing or notarization.

## Planned milestones

1. Tauri desktop UI showing preview/approve/undo and per-file status.
2. Pluggable Ollama / OpenAI-compatible AI classifier with confidence and human review.
3. Learn user corrections as auditable rules; optional folder watcher.
4. Signed installers and GitHub Releases after cross-platform integration tests.
