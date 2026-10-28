"""SortPilot desktop workbench, using native Tk widgets for a lightweight MVP."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from sortpilot import CATEGORIES, Move, execute, plan, undo, contained
from settings_store import load_settings, save_archive_settings, config_path
from archive_discovery import Root, discover, propose, validate_roots
from review_queue import choices, assign, remember, recall
from scoped_reorganization import propose_reorganization, validate_scoped_moves

BG = "#F4F7FB"
PANEL = "#FFFFFF"
NAV = "#162337"
TEXT = "#1B293B"
MUTED = "#62748B"
BLUE = "#2563EB"
FONT = "Arial"


class SortPilotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SortPilot · AI File Workspace")
        self.geometry("1120x740")
        self.minsize(900, 580)
        self.configure(bg=BG)
        self.source = tk.StringVar()
        self.destination = tk.StringVar()
        preferences = load_settings()
        self.source.set(preferences['source'])
        self.roots = [Root(**r) for r in preferences.get('roots', [])]
        self.unassigned = []
        self.inventory = None
        self.mode = tk.StringVar(value='inbox')
        self.scope = tk.StringVar()
        self.destination.set(preferences['destination'])
        self.status = tk.StringVar(value="選擇來源與目的資料夾，開始掃描")
        self.items: list[Move] = []
        self.queue: queue.Queue = queue.Queue()
        self.busy = False
        self._build()
        self.after(100, self._poll)

    def _button(self, parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command, bg=BLUE if primary else "#E8EEF7",
                         fg="white" if primary else TEXT, activebackground="#1D4ED8" if primary else "#DAE5F4",
                         activeforeground="white" if primary else TEXT, relief="flat",
                         padx=16, pady=9, font=(FONT, 10, "bold"), cursor="hand2")

    def _build(self):
        sidebar = tk.Frame(self, bg=NAV, width=205)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="✦  SortPilot", font=(FONT, 19, "bold"), fg="white", bg=NAV,
                 anchor="w").pack(fill="x", padx=22, pady=(30, 6))
        tk.Label(sidebar, text="智慧檔案整理工作台", font=(FONT, 10), fg="#A9BDD8", bg=NAV,
                 anchor="w").pack(fill="x", padx=24, pady=(0, 36))
        for title, handler in [("▣   整理檔案", lambda: self.status.set("目前位於整理檔案頁面")),
                               ("◷   整理紀錄", self.show_history),
                               ("⚙   設定", self.show_settings)]:
            tk.Button(sidebar, text=title, command=handler,
                      font=(FONT, 11, "bold"), fg="#DDE8F9",
                      bg="#233B5F" if "整理檔案" in title else NAV,
                      activebackground="#344E73", activeforeground="white",
                      cursor="hand2", relief="flat", anchor="w", padx=20, pady=14
                      ).pack(fill="x", padx=9, pady=3)
        tk.Label(sidebar, text="本機處理 · 尚未啟用 AI\nMVP 0.2 · Windows / macOS",
                 bg=NAV, fg="#94A9C6", font=(FONT, 9), justify="left").pack(side="bottom", anchor="w",
                                                                             padx=22, pady=25)
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=28, pady=25)
        tk.Label(main, text="整理檔案", font=(FONT, 22, "bold"), bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(main, text="先預覽分類結果，必要時修改目的地，再確認整理。", bg=BG, fg=MUTED,
                 font=(FONT, 10)).pack(anchor="w", pady=(4, 22))
        modes = tk.Frame(main, bg=BG)
        modes.pack(fill="x")
        tk.Radiobutton(modes, text="收件匣整理", variable=self.mode, value="inbox",
                       bg=BG, command=self._mode_changed).pack(side="left")
        tk.Radiobutton(modes, text="鎖定資料夾重整", variable=self.mode, value="scoped",
                       bg=BG, command=self._mode_changed).pack(side="left", padx=15)
        controls = tk.Frame(main, bg=PANEL, padx=20, pady=18)
        controls.pack(fill="x")
        for name, variable in [("來源資料夾", self.source)]:
            line = tk.Frame(controls, bg=PANEL)
            line.pack(fill="x", pady=6)
            tk.Label(line, text=name, width=12, anchor="w", bg=PANEL, fg=TEXT,
                     font=(FONT, 10, "bold")).pack(side="left")
            ttk.Entry(line, textvariable=variable).pack(side="left", fill="x", expand=True, padx=8)
            self._button(line, "瀏覽…", lambda v=variable: self._browse(v)).pack(side="left")
        self.scope_row = tk.Frame(controls, bg=PANEL)
        tk.Label(self.scope_row, text="鎖定資料夾", bg=PANEL, width=12).pack(side="left")
        ttk.Entry(self.scope_row, textvariable=self.scope).pack(side="left", fill="x", expand=True)
        self._button(self.scope_row, "瀏覽…", lambda: self._browse(self.scope)).pack(side="left")
        action = tk.Frame(main, bg=BG)
        action.pack(fill="x", pady=(17, 12))
        self.scan_button = self._button(action, "↻  掃描與預覽", self.scan, primary=True)
        self.scan_button.pack(side="left")
        self.apply_button = self._button(action, "✓  確認整理", self.apply)
        self.apply_button.pack(side="left", padx=10)
        self.undo_button = self._button(action, "↶  復原上次整理", self.undo_last)
        self.undo_button.pack(side="right")
        self.count_label = tk.Label(main, text="待整理檔案：0", bg=BG, fg=TEXT, font=(FONT, 11, "bold"))
        self.count_label.pack(anchor="w", pady=(5, 9))
        table_frame = tk.Frame(main, bg=PANEL)
        table_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table_frame, columns=("name", "category", "target", "reason"),
                                 show="headings", selectmode="extended")
        for column, heading, width in [("name", "檔案名稱", 215), ("category", "分類", 115),
                                       ("target", "預計目的地", 280), ("reason", "依據", 110)]:
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, minwidth=70, stretch=column == "target")
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        editor = tk.Frame(main, bg=BG)
        editor.pack(fill="x", pady=12)
        tk.Label(editor, text="選取檔案後變更分類", bg=BG, fg=TEXT).pack(side="left")
        self.category = ttk.Combobox(editor, values=[r.category for r in self.roots], state="readonly", width=22)
        self.category.pack(side="left", padx=10)
        self._button(editor, "套用到選取項目", self.change_category).pack(side="left")
        self._button(editor, "略過選取項目", self.skip_selected).pack(side="left", padx=8)
        self._button(editor, "指定小分類…", self.review_selected).pack(side="left", padx=8)
        bottom = tk.Frame(main, bg=BG)
        bottom.pack(fill="x")
        tk.Label(bottom, textvariable=self.status, bg=BG, fg=MUTED, anchor="w",
                 font=(FONT, 10)).pack(side="left", fill="x", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._select_category)
        self._mode_changed()

    def show_settings(self):
        if self.busy:
            return
        dialog = tk.Toplevel(self)
        dialog.title("SortPilot · 歸檔位置設定")
        dialog.geometry("760x510")
        dialog.configure(bg=BG)
        dialog.transient(self)
        dialog.grab_set()
        source = tk.StringVar(value=self.source.get())
        roots = list(self.roots)
        tk.Label(dialog, text="來源與歸檔位置", font=(FONT, 19, "bold"), bg=BG, fg=TEXT).pack(anchor="w", padx=22, pady=18)
        tk.Label(dialog, text="一個來源、多個已存在的目標資料夾。先設定大分類對應位置。", bg=BG, fg=MUTED).pack(anchor="w", padx=22)
        line = tk.Frame(dialog, bg=BG)
        line.pack(fill="x", padx=22, pady=12)
        ttk.Entry(line, textvariable=source).pack(side="left", fill="x", expand=True)
        self._button(line, "來源瀏覽", lambda: self._browse(source)).pack(side="left", padx=8)
        listing = tk.Listbox(dialog, height=13)
        listing.pack(fill="both", expand=True, padx=22, pady=8)
        def refresh():
            listing.delete(0, "end")
            for root in roots:
                listing.insert("end", f"{root.category}  →  {root.path}")
        refresh()
        def add():
            path = filedialog.askdirectory(title="選擇歸檔位置", parent=dialog)
            if not path:
                return
            from tkinter import simpledialog
            category = simpledialog.askstring("大分類", "此位置屬於哪個大分類？", parent=dialog)
            if category and category.strip():
                roots.append(Root(category.strip(), path))
                refresh()
        def remove():
            for index in reversed(listing.curselection()):
                del roots[index]
            refresh()
        def save():
            try:
                validate_roots(Path(source.get()), roots)
                save_archive_settings(source.get(), [vars(root) for root in roots])
            except (OSError, ValueError) as exc:
                messagebox.showerror("設定無效", str(exc), parent=dialog)
                return
            self.source.set(source.get())
            self.roots = list(roots)
            self.category.configure(values=[r.category for r in roots])
            self.items = []
            self._refresh()
            self.status.set(f"已儲存 {len(roots)} 個歸檔位置，請重新掃描")
            dialog.destroy()
        bar = tk.Frame(dialog, bg=BG)
        bar.pack(fill="x", padx=22, pady=16)
        self._button(bar, "新增歸檔位置", add).pack(side="left")
        self._button(bar, "移除選取", remove).pack(side="left", padx=8)
        self._button(bar, "儲存設定", save, primary=True).pack(side="right")

    def show_history(self):
        """History is not ready: explain rather than render a dead navigation item."""
        messagebox.showinfo("整理紀錄", "完整紀錄頁面尚在開發中；目前可使用「復原上次整理」。")

    def _browse(self, variable):
        path = filedialog.askdirectory(title="選擇資料夾")
        if path:
            variable.set(path)

    def _set_busy(self, busy):
        self.busy = busy
        state = "disabled" if busy else "normal"
        for button in (self.scan_button, self.apply_button, self.undo_button):
            button.configure(state=state)

    def _run(self, operation, callback):
        self._set_busy(True)
        def worker():
            try:
                self.queue.put((callback, operation(), None))
            except Exception as exc:
                self.queue.put((callback, None, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        try:
            while True:
                callback, result, error = self.queue.get_nowait()
                self._set_busy(False)
                if error:
                    self.status.set("發生錯誤：" + error)
                    messagebox.showerror("SortPilot", error)
                else:
                    callback(result)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _mode_changed(self):
        if not hasattr(self, "scope_row"):
            return
        if self.mode.get() == "scoped":
            self.scope_row.pack(fill="x", pady=6)
        else:
            self.scope_row.pack_forget()
        self.items = []
        self.unassigned = []
        self.inventory = None
        if hasattr(self, "tree"):
            self._refresh()

    def _scoped_scanned(self, result):
        self.items = result["moves"]
        self.unassigned = result["unresolved"]
        self.inventory = None
        self._refresh()
        self.status.set(f"鎖定根目錄：{result['scope']}；搬移建議 {len(self.items)}；"
                        f"原位保留 {result['unchanged']}；待判斷 {len(self.unassigned)}")

    def scan(self):
        if self.busy:
            return
        if self.mode.get() == "scoped":
            if not self.scope.get().strip():
                messagebox.showwarning("SortPilot", "請選擇鎖定資料夾")
                return
            self.status.set("正在掃描指定資料夾內所有檔案…")
            self._run(lambda: propose_reorganization(Path(self.scope.get())), self._scoped_scanned)
            return
        if not self.source.get() or not self.roots:
            messagebox.showwarning("SortPilot", "請先在設定中新增來源和歸檔位置")
            return
        self.status.set("正在掃描現有歸檔資料夾…")
        def task():
            inventory = discover(Path(self.source.get()), self.roots)
            return (*propose(Path(self.source.get()), inventory), inventory)
        self._run(task, self._archive_scanned)

    def _archive_scanned(self, result):
        matches, undecided, inventory = result
        self.inventory = inventory
        self.unassigned = undecided
        remembered = []
        remaining = []
        for filename in undecided:
            result = recall(filename, self.roots)
            (remembered if result else remaining).append(result if result else filename)
        self.unassigned = remaining
        self._show_plan(matches + remembered)
        self.status.set(f"索引 {inventory['folders_scanned']} 個資料夾，"
                        f"建議 {len(matches)} 個，待人工判斷 {len(undecided)} 個"
                        + ("；索引達上限" if inventory["truncated"] else ""))

    def _show_plan(self, moves):
        self.items = moves
        self._refresh()
        self.status.set(f"掃描完成：{len(moves)} 個檔案。尚未移動任何檔案。")

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        for index, item in enumerate(self.items):
            self.tree.insert("", "end", iid=str(index),
                             values=(Path(item.source).name, item.category, item.target, item.reason))
        self.count_label.configure(text=f"可確認：{len(self.items)} · 待指定：{len(self.unassigned)}")

    def _select_category(self, _event=None):
        selected = self.tree.selection()
        if selected:
            self.category.set(self.items[int(selected[0])].category)

    def change_category(self):
        if self.mode.get() == "scoped":
            messagebox.showinfo("鎖定模式", "此模式暫不支援改用其他根目錄。")
            return
        category = self.category.get()
        if category not in [r.category for r in self.roots]:
            return
        matching = [root for root in self.roots if root.category == category]
        if len(matching) != 1:
            messagebox.showwarning("設定問題", "此大分類必須恰好對應一個歸檔根目錄")
            return
        for key in self.tree.selection():
            item = self.items[int(key)]
            item.category = category
            item.target = str(Path(matching[0].path).resolve() / Path(item.target).name)
            item.reason = "manual category"
        self._refresh()
        self.status.set("已更新預覽，尚未移動檔案。")

    def review_selected(self):
        if self.mode.get() == "scoped":
            messagebox.showinfo("鎖定模式", "人工指定子資料夾功能仍在開發，暫時僅有既有目錄建議。")
            return
        if self.busy or not self.inventory:
            messagebox.showinfo("待確認", "請先掃描歸檔資料夾")
            return
        selected = [self.items[int(key)].source for key in self.tree.selection()]
        filenames = selected or list(self.unassigned)
        if not filenames:
            messagebox.showinfo("待確認", "目前沒有需要指定的檔案")
            return
        options = choices(self.roots, self.inventory)
        if not options:
            messagebox.showwarning("待確認", "找不到可以使用的既有資料夾")
            return
        dialog = tk.Toplevel(self)
        dialog.title("SortPilot · 人工分類審核")
        dialog.geometry("840x530")
        dialog.configure(bg=BG)
        dialog.transient(self)
        dialog.grab_set()
        tk.Label(dialog, text="人工確認歸檔位置", font=(FONT, 18, "bold"), bg=BG, fg=TEXT).pack(
            anchor="w", padx=20, pady=14)
        tk.Label(dialog, text="選擇檔案，並從已存在的分類資料夾中指定目的地。可記住完整檔名規則。",
                 bg=BG, fg=MUTED).pack(anchor="w", padx=20)
        left = tk.Listbox(dialog, height=14, exportselection=False)
        left.pack(fill="both", expand=True, padx=20, pady=12)
        for file in filenames:
            left.insert("end", Path(file).name)
        right = tk.Frame(dialog, bg=BG)
        right.pack(fill="x", padx=20)
        folder_choice = ttk.Combobox(right, state="readonly", width=85,
                                     values=[f"{category} → {folder}" for category, folder in options])
        folder_choice.pack(side="left", fill="x", expand=True)
        folder_choice.current(0)
        keep_rule = tk.BooleanVar(value=True)
        tk.Checkbutton(dialog, text="記住這個完整檔名的歸檔位置（下次仍需確認）",
                       variable=keep_rule, bg=BG, fg=TEXT).pack(anchor="w", padx=20, pady=8)
        def apply_choice():
            selection = left.curselection()
            if not selection:
                messagebox.showwarning("待確認", "請先選擇一個檔案", parent=dialog)
                return
            original = filenames[selection[0]]
            category, folder = options[folder_choice.current()]
            try:
                move = assign(original, category, folder, self.roots)
                if keep_rule.get():
                    remember(move, self.roots)
            except (OSError, ValueError) as exc:
                messagebox.showerror("指派失敗", str(exc), parent=dialog)
                return
            self.items = [item for item in self.items if item.source != original]
            self.items.append(move)
            self.unassigned = [item for item in self.unassigned if item != original]
            self._refresh()
            del filenames[selection[0]]
            left.delete(selection[0])
            self.status.set("已加入整理預覽，尚未搬移檔案。")
            if not filenames:
                dialog.destroy()
        bar = tk.Frame(dialog, bg=BG)
        bar.pack(fill="x", padx=20, pady=15)
        self._button(bar, "套用到選取檔案", apply_choice, primary=True).pack(side="left")
        self._button(bar, "完成", dialog.destroy).pack(side="right")

    def skip_selected(self):
        selected = {int(key) for key in self.tree.selection()}
        self.items = [item for i, item in enumerate(self.items) if i not in selected]
        self._refresh()
        self.status.set("已從本次整理計畫略過選取檔案。")

    def apply(self):
        if self.busy or not self.items:
            return
        if not messagebox.askyesno("確認搬移", f"確定移動 {len(self.items)} 個檔案嗎？\n此操作會修改磁碟內容。"):
            return
        moves = [Move(**vars(item)) for item in self.items]
        if self.mode.get() == "scoped":
            try:
                validate_scoped_moves(Path(self.scope.get()), moves)
            except (OSError, ValueError) as exc:
                messagebox.showerror("鎖定範圍驗證失敗", str(exc))
                return
        dest = config_path().parent / "journal"
        self.status.set("正在整理檔案…")
        self._run(lambda: execute(moves, dest), self._applied)

    def _applied(self, result):
        batch, moves = result
        self.items = []
        self._refresh()
        self.status.set(f"完成 {len(moves)} 個檔案 · 批次 {batch[:8]}。可使用復原。")
        messagebox.showinfo("整理完成", f"已搬移 {len(moves)} 個檔案。")

    def undo_last(self):
        if self.busy:
            return
        if not messagebox.askyesno("復原", "復原最後一批尚未復原的整理記錄？\n已修改的檔案將保留原位。"):
            return
        dest = config_path().parent / "journal"
        self.status.set("正在復原…")
        self._run(lambda: undo(dest), self._undone)

    def _undone(self, result):
        self.status.set(f"已復原 {len(result['restored'])} 個檔案；略過 {len(result['skipped'])} 個。")
        messagebox.showinfo("復原結果", self.status.get())


if __name__ == "__main__":
    SortPilotApp().mainloop()
