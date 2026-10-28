# SortPilot

Windows / macOS cross-platform, local-first file organizer. **MVP 0.2 includes a working desktop GUI** for preview, manual adjustments, confirmed file moves, and Undo. The current classifier uses file extensions; **AI content analysis, learning, background monitoring, and the planned Tauri frontend are not yet implemented**.

## Desktop GUI

Run from source with Python 3.10+ and Tkinter:

```sh
python desktop.py
```

Use the interface to select a source folder and a *separate, non-nested* destination folder, then:

1. **掃描與預覽** lists only top-level regular non-hidden files. No files move.
2. Select one or more rows and **套用到選取項目** to change their destination category.
3. **略過選取項目** excludes rows from this batch.
4. **確認整理** displays a confirmation dialog before moving files.
5. **復原上次整理** restores only unchanged files without overwriting their original paths.

Categories are currently based on file suffix; the interface intentionally says **尚未啟用 AI**. The history/settings navigation labels are placeholders and not interactive yet.

## Cross-platform build

GitHub Actions runs tests on Ubuntu / Windows / macOS and builds PyInstaller standalone GUI artifacts on Windows and macOS. View the most recent run under **Actions → Build and test → Artifacts**.

- Windows: `SortPilot.exe` (standalone GUI)
- macOS: `SortPilot.app` (inside the macOS artifact ZIP; unsigned, unnotarized)

Builds are **artifacts, not signed installers or GitHub Releases**. macOS Gatekeeper may block unsigned builds. The source GUI uses Tkinter, not Tauri, to deliver a functional first desktop prototype rapidly. A Tauri + Rust UI remains a potential later rewrite.

## CLI

```sh
python sortpilot.py plan "/path/to/Downloads" "/path/to/Sorted"
python sortpilot.py apply "/path/to/Downloads" "/path/to/Sorted" --confirm
python sortpilot.py undo "/path/to/Sorted"
python -m unittest discover -s tests -v
```

## Safety and known limitations

- Preview is default. Moving files requires explicit approval.
- Source/destination must be separate non-nested directories.
- Symlinks, hidden files, and subdirectories are skipped; no recursive traversal.
- File collisions get numeric suffixes; existing files are not overwritten.
- Undo journal uses SQLite and SHA-256. Files changed after moving are not restored.
- No deletion, AI provider, rule-learning, PDF parsing, auto-monitoring, folder-tree browser or per-file naming editor.
- If a crash happens between moving and writing the journal entry, manual recovery may be required. Use a small backed-up test folder first.
- GUI is intentionally a native MVP; design polish, actual tab navigation, accessibility, signing, and end-to-end packaging validation are future work.

## Next milestones

1. Implement an explicit review queue and human-editable naming/target paths with safe validation.
2. Integrate optional Ollama / cloud AI with strict privacy controls and fallback rules.
3. Save approved correction rules and add audit/recovery history UI.
4. Refine UX and investigate migration to Tauri with cross-platform native installers.
