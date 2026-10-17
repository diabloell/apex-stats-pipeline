import json
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from main import build_jobs

ROOT = Path(__file__).resolve().parent
JSX = ROOT / "photoshop" / "fill_from_json.jsx"

def launch_photoshop(job_file):
    source = JSX.read_text(encoding="utf-8-sig")
    to_replace = 'var file = File.openDialog("Choose JSON exported by main.py", "JSON files:*.json");'
    if source.count(to_replace) != 1:
        raise RuntimeError("Cannot find JSON picker in Photoshop script: perhaps JSX changed")
    replacement = "var file = new File(" + json.dumps(str(job_file), ensure_ascii=False) + ");"
    script = source.replace(to_replace, replacement)
    generated = ROOT / "output" / "photoshop" / "_run_selected.jsx"
    generated.write_text(script, encoding="utf-8-sig")

    quoted = str(generated).replace("'", "''")
    command = (
        "$ErrorActionPreference = 'Stop'; "
        "$ps = New-Object -ComObject Photoshop.Application; "
        "$ps.DoJavaScriptFile('" + quoted + "')"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, timeout=180,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Photoshop COM failed")

class Launcher:
    def __init__(self, root):
        self.root = root
        root.title("Apex Stats Pipeline")
        root.resizable(False, False)
        frame = ttk.Frame(root, padding=20)
        frame.grid()
        root.columnconfigure(0, weight=1)

        self.source = tk.StringVar(value="eternal")
        self.job_type = tk.StringVar(value="table")
        self.match_number = tk.StringVar(value="5")
        self.event = tk.StringVar(value="ALGS CHAMPIONSHIP 2025")
        self.als_url = tk.StringVar()
        self.auto = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Готов к экспорту")

        ttk.Label(frame, text="Источник результатов").grid(row=0, column=0, sticky="w")
        choices = ttk.Combobox(frame, textvariable=self.source, width=36, state="readonly",
                               values=("eternal", "als"))
        choices.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 10))

        ttk.Label(frame, text="Ссылка ALS на конкретную серию (только для als)").grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Entry(frame, textvariable=self.als_url, width=68).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 10))
        ttk.Label(frame, text="Название турнира").grid(row=4, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.event, width=48).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(2, 10))

        ttk.Label(frame, text="Тип поста").grid(row=6, column=0, sticky="w")
        ttk.Combobox(frame, textvariable=self.job_type, values=("table", "mvp"),
                     state="readonly", width=20).grid(row=7, column=0, sticky="w", pady=(2, 10))
        ttk.Label(frame, text="Номер матча (MVP)").grid(row=6, column=1, sticky="w")
        ttk.Spinbox(frame, from_=1, to=40, textvariable=self.match_number,
                    width=8).grid(row=7, column=1, sticky="w", pady=(2, 10))

        ttk.Checkbutton(frame, text="Автоматически запустить Photoshop (экспериментально)",
                        variable=self.auto).grid(row=8, column=0, columnspan=2, sticky="w", pady=(0, 13))
        self.button = ttk.Button(frame, text="Создать PSD и PNG", command=self.run)
        self.button.grid(row=9, column=0, columnspan=2, sticky="ew", ipady=7)
        ttk.Label(frame, textvariable=self.status, wraplength=500).grid(
            row=10, column=0, columnspan=2, sticky="w", pady=(14, 0))

    def run(self):
        try:
            number = int(self.match_number.get())
            if number < 1:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Ошибка", "Номер матча должен быть положительным целым числом")
            return
        options = (self.source.get(), number, self.event.get().strip(),
                   self.job_type.get(), self.als_url.get().strip(), self.auto.get())
        if options[0] == "als" and not options[4]:
            messagebox.showerror("Ошибка", "Вставь ссылку ALS на конкретную серию (не Overview)")
            return
        self.button.state(["disabled"])
        self.status.set("Обработка статистики...")
        threading.Thread(target=self._work, args=(options,), daemon=True).start()

    def _work(self, options):
        source, match_num, event, job_type, als_url, auto = options
        try:
            jobs, data = build_jobs(source, match_num, event, job_type, als_url or None,
                                    fast=(job_type == "table" and source == "als"))
            warnings = data.get("warnings", [])
            note = "\n".join("• " + x for x in warnings[:7])
            if auto:
                self._set_status("JSON создан. Запускаю Photoshop...")
                try:
                    for job in jobs:
                        launch_photoshop(job)
                    self._finished("Экспорт выполнен. Проверь PSD/PNG в output/photoshop.\n" + note)
                except Exception as exc:
                    self._finished("JSON создан, но автоматический Photoshop не запустился:\n"
                                   + str(exc) + "\n\nЗапасной способ: Файл → Сценарии → Обзор → "
                                   "photoshop/fill_from_json.jsx; выбери: " + jobs[0].name)
            else:
                self._finished("JSON готов: " + ", ".join(x.name for x in jobs)
                               + ".\nВ Photoshop: Файл → Сценарии → Обзор → "
                               "photoshop/fill_from_json.jsx.\n" + note)
        except Exception as exc:
            self._finished("Ошибка: " + str(exc))

    def _set_status(self, text):
        self.root.after(0, lambda: self.status.set(text))

    def _finished(self, text):
        def finish():
            self.status.set(text)
            self.button.state(["!disabled"])
        self.root.after(0, finish)

if __name__ == "__main__":
    root = tk.Tk()
    Launcher(root)
    root.mainloop()
