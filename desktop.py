"""SortPilot desktop workbench, using native Tk widgets for a lightweight MVP."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from sortpilot import CATEGORIES, Move, execute, plan, undo

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
        for title in ["▣   整理檔案", "◷   整理紀錄", "⚙   設定"]:
            tk.Label(sidebar, text=title, font=(FONT, 11, "bold"), fg="#DDE8F9",
                     bg="#233B5F" if "整理檔案" in title else NAV,
                     anchor="w", padx=20, pady=14).pack(fill="x", padx=9, pady=3)
        tk.Label(sidebar, text="本機處理 · 尚未啟用 AI\nMVP 0.2 · Windows / macOS",
                 bg=NAV, fg="#94A9C6", font=(FONT, 9), justify="left").pack(side="bottom", anchor="w",
                                                                             padx=22, pady=25)
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=28, pady=25)
        tk.Label(main, text="整理檔案", font=(FONT, 22, "bold"), bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(main, text="先預覽分類結果，必要時修改目的地，再確認整理。", bg=BG, fg=MUTED,
                 font=(FONT, 10)).pack(anchor="w", pady=(4, 22))
        controls = tk.Frame(main, bg=PANEL, padx=20, pady=18)
        controls.pack(fill="x")
        for name, variable in [("來源資料夾", self.source), ("整理目的地", self.destination)]:
            line = tk.Frame(controls, bg=PANEL)
            line.pack(fill="x", pady=6)
            tk.Label(line, text=name, width=12, anchor="w", bg=PANEL, fg=TEXT,
                     font=(FONT, 10, "bold")).pack(side="left")
            ttk.Entry(line, textvariable=variable).pack(side="left", fill="x", expand=True, padx=8)
            self._button(line, "瀏覽…", lambda v=variable: self._browse(v)).pack(side="left")
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
        self.category = ttk.Combobox(editor, values=list(CATEGORIES) + ["Other"], state="readonly", width=22)
        self.category.pack(side="left", padx=10)
        self._button(editor, "套用到選取項目", self.change_category).pack(side="left")
        self._button(editor, "略過選取項目", self.skip_selected).pack(side="left", padx=8)
        bottom = tk.Frame(main, bg=BG)
        bottom.pack(fill="x")
        tk.Label(bottom, textvariable=self.status, bg=BG, fg=MUTED, anchor="w",
                 font=(FONT, 10)).pack(side="left", fill="x", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._select_category)

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

    def scan(self):
        if self.busy:
            return
        source, destination = Path(self.source.get()), Path(self.destination.get())
        if not self.source.get() or not self.destination.get():
            messagebox.showwarning("SortPilot", "請先選擇來源及整理目的地")
            return
        self.status.set("正在掃描…")
        self._run(lambda: plan(source, destination), self._show_plan)

    def _show_plan(self, moves):
        self.items = moves
        self._refresh()
        self.status.set(f"掃描完成：{len(moves)} 個檔案。尚未移動任何檔案。")

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        for index, item in enumerate(self.items):
            self.tree.insert("", "end", iid=str(index),
                             values=(Path(item.source).name, item.category, item.target, item.reason))
        self.count_label.configure(text=f"待整理檔案：{len(self.items)}")

    def _select_category(self, _event=None):
        selected = self.tree.selection()
        if selected:
            self.category.set(self.items[int(selected[0])].category)

    def change_category(self):
        category = self.category.get()
        if category not in (*CATEGORIES.keys(), "Other"):
            return
        for key in self.tree.selection():
            item = self.items[int(key)]
            item.category = category
            item.target = str(Path(self.destination.get()).resolve() / category / Path(item.target).name)
            item.reason = "manual category"
        self._refresh()
        self.status.set("已更新預覽，尚未移動檔案。")

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
        dest = Path(self.destination.get()).resolve()
        self.status.set("正在整理檔案…")
        self._run(lambda: execute(moves, dest), self._applied)

    def _applied(self, result):
        batch, moves = result
        self.items = []
        self._refresh()
        self.status.set(f"完成 {len(moves)} 個檔案 · 批次 {batch[:8]}。可使用復原。")
        messagebox.showinfo("整理完成", f"已搬移 {len(moves)} 個檔案。")

    def undo_last(self):
        if self.busy or not self.destination.get():
            return
        if not messagebox.askyesno("復原", "復原最後一批尚未復原的整理記錄？\n已修改的檔案將保留原位。"):
            return
        dest = Path(self.destination.get()).resolve()
        self.status.set("正在復原…")
        self._run(lambda: undo(dest), self._undone)

    def _undone(self, result):
        self.status.set(f"已復原 {len(result['restored'])} 個檔案；略過 {len(result['skipped'])} 個。")
        messagebox.showinfo("復原結果", self.status.get())


if __name__ == "__main__":
    SortPilotApp().mainloop()
