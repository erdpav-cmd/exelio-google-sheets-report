"""Tkinter-приложение: параметры отчёта → симуляция → Google Таблица."""

from __future__ import annotations

import calendar
import getpass
import os
import threading
import tkinter as tk
import webbrowser
from datetime import date
from tkinter import messagebox, ttk

from google_sheets import DEFAULT_SPREADSHEET_ID, GoogleSheetsClient, GoogleSheetsError
from report_data import (
    DEPARTMENTS,
    REGIONS,
    REPORT_TYPES,
    ReportParams,
    parse_ru_date,
    simulate_report,
)
from report_writer import write_report


NAVY = "#1B3A4B"
GOLD = "#C4A35A"
CREAM = "#F4EFE6"
PAPER = "#FFFEFA"
TEXT = "#1C2428"
MUTED = "#5B6A72"


class DateField(ttk.Frame):
    """Поле даты ДД.ММ.ГГГГ с выпадающим календарём."""

    def __init__(self, master: tk.Misc, initial: date) -> None:
        super().__init__(master)
        self._popup: tk.Toplevel | None = None
        self.var = tk.StringVar(value=initial.strftime("%d.%m.%Y"))
        entry = ttk.Entry(self, textvariable=self.var, width=12)
        entry.pack(side=tk.LEFT, ipady=2)
        ttk.Button(self, text="▾", width=3, command=self._open).pack(side=tk.LEFT, padx=(4, 0))

    def get(self) -> date:
        return parse_ru_date(self.var.get())

    def _open(self) -> None:
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.lift()
            return
        try:
            current = self.get()
        except ValueError:
            current = date.today()

        popup = tk.Toplevel(self)
        self._popup = popup
        popup.title("Дата")
        popup.resizable(False, False)
        popup.transient(self.winfo_toplevel())
        popup.configure(bg=PAPER)
        popup.grab_set()

        year = current.year
        month = current.month
        grid = ttk.Frame(popup, padding=8)
        grid.pack()

        header = ttk.Frame(grid)
        header.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 6))
        title = ttk.Label(header, font=("Segoe UI", 10, "bold"))
        title.pack(side=tk.LEFT, expand=True)

        def redraw() -> None:
            for child in grid.grid_slaves():
                info = child.grid_info()
                if int(info["row"]) >= 2:
                    child.destroy()
            months = (
                "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
            )
            title.configure(text=f"{months[month - 1]} {year}")
            cal = calendar.Calendar(firstweekday=0)
            weeks = cal.monthdayscalendar(year, month)
            for r, week in enumerate(weeks, start=2):
                for c, day in enumerate(week):
                    if day == 0:
                        ttk.Label(grid, text="", width=4).grid(row=r, column=c)
                        continue
                    chosen = date(year, month, day)

                    def pick(value: date = chosen) -> None:
                        self.var.set(value.strftime("%d.%m.%Y"))
                        popup.destroy()

                    btn = ttk.Button(grid, text=str(day), width=4, command=pick)
                    btn.grid(row=r, column=c, padx=1, pady=1)

        def shift(delta: int) -> None:
            nonlocal year, month
            month += delta
            if month < 1:
                month, year = 12, year - 1
            elif month > 12:
                month, year = 1, year + 1
            redraw()

        ttk.Button(header, text="‹", width=3, command=lambda: shift(-1)).pack(side=tk.LEFT)
        ttk.Button(header, text="›", width=3, command=lambda: shift(1)).pack(side=tk.RIGHT)

        for i, name in enumerate(("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")):
            ttk.Label(grid, text=name, width=4, anchor="center").grid(row=1, column=i)

        redraw()
        popup.geometry(f"+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height()}")
        popup.protocol("WM_DELETE_WINDOW", popup.destroy)


class ReportApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("EXELIO — формирование отчёта")
        self.geometry("560x720")
        self.minsize(520, 680)
        self.configure(bg=CREAM)
        self._busy = False
        self._last_url = ""

        self._style()
        self._build()

    def _style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("TFrame", background=PAPER)
        style.configure("Card.TFrame", background=PAPER)
        style.configure("TLabel", background=PAPER, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=PAPER, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=NAVY, foreground=PAPER, font=("Georgia", 18, "bold"))
        style.configure("Sub.TLabel", background=NAVY, foreground=GOLD, font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"))
        style.configure("TCombobox", padding=4)
        style.configure("TEntry", padding=4)

    def _build(self) -> None:
        header = tk.Frame(self, bg=NAVY)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="EXELIO",
            bg=NAVY,
            fg=PAPER,
            font=("Georgia", 20, "bold"),
        ).pack(pady=(18, 2))
        tk.Label(
            header,
            text="Симулятор аналитического отчёта для Google Таблиц",
            bg=NAVY,
            fg=GOLD,
            font=("Segoe UI", 10),
        ).pack(pady=(0, 16))
        tk.Frame(self, bg=GOLD, height=4).pack(fill=tk.X)

        body = ttk.Frame(self, style="Card.TFrame", padding=24)
        body.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)

        ttk.Label(body, text="Период отчёта").grid(row=0, column=0, sticky="w")
        period = ttk.Frame(body)
        period.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 14))
        today = date.today()
        month_start = today.replace(day=1)
        ttk.Label(period, text="с").pack(side=tk.LEFT, padx=(0, 6))
        self.date_from = DateField(period, month_start)
        self.date_from.pack(side=tk.LEFT)
        ttk.Label(period, text="по").pack(side=tk.LEFT, padx=(12, 6))
        self.date_to = DateField(period, today)
        self.date_to.pack(side=tk.LEFT)

        self.report_type = self._combo(body, 2, "Тип отчёта", REPORT_TYPES)
        self.department = self._combo(body, 4, "Подразделение", DEPARTMENTS)
        self.region = self._combo(body, 6, "Регион", REGIONS)

        ttk.Label(body, text="Ответственный").grid(row=8, column=0, sticky="w")
        self.author = ttk.Entry(body, width=42)
        self.author.insert(0, getpass.getuser())
        self.author.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(4, 12))

        ttk.Label(body, text="Комментарий (необязательно)").grid(row=10, column=0, sticky="w")
        self.notes = tk.Text(body, height=4, width=42, font=("Segoe UI", 10), wrap=tk.WORD, relief=tk.SOLID, bd=1)
        self.notes.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(4, 16))

        self.submit = ttk.Button(
            body,
            text="Сформировать отчёт и записать в таблицу",
            style="Accent.TButton",
            command=self._on_submit,
        )
        self.submit.grid(row=12, column=0, columnspan=2, sticky="ew", ipady=6)

        self.open_btn = ttk.Button(
            body,
            text="Открыть последнюю таблицу",
            command=self._open_last,
            state=tk.DISABLED,
        )
        self.open_btn.grid(row=13, column=0, columnspan=2, sticky="ew", pady=(8, 0), ipady=2)

        self.status = ttk.Label(
            body,
            text="Заполните поля и нажмите кнопку — данные будут симулированы.",
            style="Muted.TLabel",
            wraplength=480,
        )
        self.status.grid(row=14, column=0, columnspan=2, sticky="w", pady=(16, 8))

        self.preview = ttk.Label(body, text="", wraplength=480, justify=tk.LEFT)
        self.preview.grid(row=15, column=0, columnspan=2, sticky="w")

        body.columnconfigure(0, weight=1)

    def _combo(self, parent: ttk.Frame, row: int, label: str, values: tuple[str, ...]) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        box = ttk.Combobox(parent, values=values, state="readonly", width=40)
        box.set(values[0])
        box.grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=(4, 12))
        return box

    def _on_submit(self) -> None:
        if self._busy:
            return
        try:
            params = ReportParams(
                date_from=self.date_from.get(),
                date_to=self.date_to.get(),
                report_type=self.report_type.get().strip(),
                department=self.department.get().strip(),
                region=self.region.get().strip(),
                author=self.author.get().strip() or "Не указан",
                notes=self.notes.get("1.0", tk.END).strip(),
            )
        except ValueError as exc:
            messagebox.showerror("Проверьте поля", str(exc))
            return

        self._busy = True
        self.submit.configure(state=tk.DISABLED)
        self.status.configure(text="Симулирую данные и записываю документ в Google Таблицу…")
        self.preview.configure(text="")
        threading.Thread(target=self._worker, args=(params,), daemon=True).start()

    def _worker(self, params: ReportParams) -> None:
        try:
            report = simulate_report(params)
            spreadsheet_id = os.getenv("SPREADSHEET_ID", "").strip() or DEFAULT_SPREADSHEET_ID
            client = GoogleSheetsClient(spreadsheet_id=spreadsheet_id)
            url = write_report(client, report)
            preview = "   ·   ".join(report.highlights)
            self.after(0, lambda: self._done(True, url, preview, ""))
        except (GoogleSheetsError, FileNotFoundError, ValueError, OSError) as exc:
            message = str(exc)
            self.after(0, lambda: self._done(False, "", "", message))
        except Exception as exc:  # noqa: BLE001 — показать любую ошибку API в GUI
            message = f"Не удалось сформировать отчёт: {exc}"
            self.after(0, lambda: self._done(False, "", "", message))

    def _done(self, ok: bool, url: str, preview: str, error: str) -> None:
        self._busy = False
        self.submit.configure(state=tk.NORMAL)
        if ok:
            self._last_url = url
            self.open_btn.configure(state=tk.NORMAL)
            self.status.configure(text="Готово. Отчёт записан отдельным листом в Google Таблицу.")
            self.preview.configure(text=preview)
            if messagebox.askyesno("Отчёт готов", "Документ создан.\nОткрыть Google Таблицу?"):
                webbrowser.open(url)
        else:
            self.status.configure(text=error)
            messagebox.showerror("Ошибка", error)

    def _open_last(self) -> None:
        if self._last_url:
            webbrowser.open(self._last_url)
        else:
            spreadsheet_id = os.getenv("SPREADSHEET_ID", "").strip() or DEFAULT_SPREADSHEET_ID
            webbrowser.open(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")


def main() -> None:
    app = ReportApp()
    app.mainloop()


if __name__ == "__main__":
    main()
