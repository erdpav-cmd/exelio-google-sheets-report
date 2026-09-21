"""Запись симулированного отчёта в Google Таблицу в виде документа."""

from __future__ import annotations

from typing import Any

from google_sheets import GoogleSheetsClient
from report_data import SimulatedReport


COLS = 6  # A–F
NAVY = "#1B3A4B"
NAVY_SOFT = "#2B5163"
GOLD = "#C4A35A"
CREAM = "#F4EFE6"
PAPER = "#FFFEFA"
ALT = "#F3F0E8"
KPI = "#E7EEF1"
WHITE = "#FFFFFF"
TEXT = "#1C2428"
MUTED = "#5B6A72"
GREEN = "#2F6B4F"
RED = "#9C3B3B"
LINE = "#D8D2C6"


def rgb(hex_color: str) -> dict[str, float]:
    value = hex_color.lstrip("#")
    return {
        "red": int(value[0:2], 16) / 255,
        "green": int(value[2:4], 16) / 255,
        "blue": int(value[4:6], 16) / 255,
    }


def _compose(report: SimulatedReport) -> tuple[
    list[list[Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[int],
    int,
]:
    values: list[list[Any]] = []
    merges: list[dict[str, Any]] = []
    formats: list[dict[str, Any]] = []
    heights: list[int] = []

    def row_index() -> int:
        return len(values)

    def add(cells: list[Any], height: int = 22) -> int:
        padded = list(cells) + [""] * (COLS - len(cells))
        values.append(padded[:COLS])
        heights.append(height)
        return len(values) - 1

    def merge(r: int, c0: int = 0, c1: int = COLS, r1: int | None = None) -> None:
        merges.append(_merge(r, r1 if r1 is not None else r + 1, c0, c1))

    def fmt(r0: int, r1: int, c0: int, c1: int, **kwargs: Any) -> None:
        formats.append(_repeat(r0, r1, c0, c1, **kwargs))

    p = report.params
    period = f"{p.date_from:%d.%m.%Y}  —  {p.date_to:%d.%m.%Y}"

    # 0: верхний кант
    add([""] * COLS, 10)
    fmt(0, 1, 0, COLS, bg=NAVY)

    # 1: шапка документа
    r = add(
        ["EXELIO  ·  ВНУТРЕННИЙ АНАЛИТИЧЕСКИЙ ДОКУМЕНТ", "", "", "", "", report.report_no],
        28,
    )
    merge(r, 0, 4)
    fmt(r, r + 1, 0, 4, bg=NAVY, fg=WHITE, size=10, bold=True, h="LEFT", indent=1)
    fmt(r, r + 1, 4, COLS, bg=NAVY, fg=GOLD, size=10, bold=True, h="RIGHT")

    # 2: название
    r = add([report.title] + [""] * 5, 42)
    merge(r)
    fmt(r, r + 1, 0, COLS, bg=NAVY, fg=WHITE, size=20, bold=True, h="CENTER", font="Georgia")

    # 3: период
    r = add([f"за период {period}"] + [""] * 5, 24)
    merge(r)
    fmt(r, r + 1, 0, COLS, bg=NAVY, fg=GOLD, size=11, italic=True, h="CENTER")

    # 4: золотая линия
    r = add([""] * COLS, 6)
    fmt(r, r + 1, 0, COLS, bg=GOLD)

    # 5: воздух
    add([""] * COLS, 12)
    fmt(5, 6, 0, COLS, bg=PAPER)

    # 6–7: реквизиты
    r = add(
        [
            "Подразделение",
            p.department,
            "",
            "Ответственный",
            p.author,
            "",
        ],
        24,
    )
    merge(r, 1, 3)
    merge(r, 4, COLS)
    fmt(r, r + 1, 0, 1, bg=PAPER, fg=MUTED, size=9, bold=True)
    fmt(r, r + 1, 1, 3, bg=PAPER, fg=TEXT, size=11, bold=True)
    fmt(r, r + 1, 3, 4, bg=PAPER, fg=MUTED, size=9, bold=True)
    fmt(r, r + 1, 4, COLS, bg=PAPER, fg=TEXT, size=11, bold=True)

    r = add(
        [
            "Регион",
            p.region,
            "",
            "Сформирован",
            report.generated_at.strftime("%d.%m.%Y  %H:%M"),
            "",
        ],
        24,
    )
    merge(r, 1, 3)
    merge(r, 4, COLS)
    fmt(r, r + 1, 0, 1, bg=PAPER, fg=MUTED, size=9, bold=True)
    fmt(r, r + 1, 1, 3, bg=PAPER, fg=TEXT, size=11)
    fmt(r, r + 1, 3, 4, bg=PAPER, fg=MUTED, size=9, bold=True)
    fmt(r, r + 1, 4, COLS, bg=PAPER, fg=TEXT, size=11)
    fmt(r, r + 1, 0, COLS, bottom=GOLD, bottom_w=1)

    add([""] * COLS, 14)
    fmt(row_index() - 1, row_index(), 0, COLS, bg=PAPER)

    # секция KPI
    r = add(["1. Сводные показатели"] + [""] * 5, 28)
    merge(r)
    fmt(r, r + 1, 0, COLS, bg=NAVY_SOFT, fg=WHITE, size=12, bold=True, h="LEFT", indent=1)

    add([""] * COLS, 8)
    fmt(row_index() - 1, row_index(), 0, COLS, bg=PAPER)

    label_row = add([""] * COLS, 20)
    value_row = add([""] * COLS, 34)
    hint_row = add([""] * COLS, 20)
    for i, (name, value, hint) in enumerate(report.kpis[:3]):
        c0, c1 = i * 2, i * 2 + 2
        values[label_row][c0] = name
        values[value_row][c0] = value
        values[hint_row][c0] = hint
        merge(label_row, c0, c1)
        merge(value_row, c0, c1)
        merge(hint_row, c0, c1)
        fmt(label_row, label_row + 1, c0, c1, bg=KPI, fg=MUTED, size=9, bold=True, h="CENTER")
        fmt(value_row, value_row + 1, c0, c1, bg=KPI, fg=NAVY, size=14, bold=True, h="CENTER")
        fmt(hint_row, hint_row + 1, c0, c1, bg=KPI, fg=MUTED, size=8, italic=True, h="CENTER")

    add([""] * COLS, 8)
    fmt(row_index() - 1, row_index(), 0, COLS, bg=PAPER)

    label_row = add([""] * COLS, 20)
    value_row = add([""] * COLS, 34)
    hint_row = add([""] * COLS, 20)
    # четвёртый KPI + два highlights
    extras = [
        report.kpis[3] if len(report.kpis) > 3 else ("Показатель", "—", ""),
        ("Лидер структуры", report.categories[0].name, f"{report.categories[0].share * 100:.1f}% доли"),
        (
            "Зона внимания",
            min(report.categories, key=lambda row: row.change).name,
            "слабая динамика",
        ),
    ]
    for i, (name, value, hint) in enumerate(extras):
        c0, c1 = i * 2, i * 2 + 2
        values[label_row][c0] = name
        values[value_row][c0] = value
        values[hint_row][c0] = hint
        merge(label_row, c0, c1)
        merge(value_row, c0, c1)
        merge(hint_row, c0, c1)
        fmt(label_row, label_row + 1, c0, c1, bg=KPI, fg=MUTED, size=9, bold=True, h="CENTER")
        fmt(value_row, value_row + 1, c0, c1, bg=KPI, fg=NAVY, size=13, bold=True, h="CENTER")
        fmt(hint_row, hint_row + 1, c0, c1, bg=KPI, fg=MUTED, size=8, italic=True, h="CENTER")

    add([""] * COLS, 16)
    fmt(row_index() - 1, row_index(), 0, COLS, bg=PAPER)

    # таблица категорий
    r = add([report.table_title] + [""] * 5, 28)
    merge(r)
    fmt(r, r + 1, 0, COLS, bg=NAVY_SOFT, fg=WHITE, size=12, bold=True, h="LEFT", indent=1)

    headers = list(report.table_headers) + [""]
    r = add(headers[:COLS], 26)
    fmt(r, r + 1, 0, COLS, bg=NAVY, fg=WHITE, size=9, bold=True, h="CENTER")

    table_start = row_index()
    for i, item in enumerate(report.categories):
        r = add(
            [
                item.name,
                item.quantity,
                item.amount,
                item.share,
                item.change,
                "",
            ],
            24,
        )
        bg = PAPER if i % 2 == 0 else ALT
        fmt(r, r + 1, 0, 1, bg=bg, fg=TEXT, size=10, h="LEFT", indent=1)
        fmt(r, r + 1, 1, 2, bg=bg, fg=TEXT, size=10, h="CENTER", number="#,##0")
        fmt(r, r + 1, 2, 3, bg=bg, fg=TEXT, size=10, h="RIGHT", number='#,##0" ₽"')
        fmt(r, r + 1, 3, 4, bg=bg, fg=TEXT, size=10, h="CENTER", number="0.0%")
        delta_fg = GREEN if item.change >= 0 else RED
        fmt(
            r,
            r + 1,
            4,
            5,
            bg=bg,
            fg=delta_fg,
            size=10,
            bold=True,
            h="CENTER",
            number="+0.0%;-0.0%;0.0%",
        )
        fmt(r, r + 1, 5, 6, bg=bg)

    r = add(
        [
            "ИТОГО",
            report.total_volume,
            report.total_amount,
            1,
            "",
            "",
        ],
        28,
    )
    fmt(r, r + 1, 0, 1, bg=GOLD, fg=NAVY, size=10, bold=True, h="LEFT", indent=1)
    fmt(r, r + 1, 1, 2, bg=GOLD, fg=NAVY, size=10, bold=True, h="CENTER", number="#,##0")
    fmt(r, r + 1, 2, 3, bg=GOLD, fg=NAVY, size=10, bold=True, h="RIGHT", number='#,##0" ₽"')
    fmt(r, r + 1, 3, 4, bg=GOLD, fg=NAVY, size=10, bold=True, h="CENTER", number="0%")
    fmt(r, r + 1, 4, COLS, bg=GOLD)
    table_end = r + 1
    formats.append(_outer_border(table_start - 1, table_end, 0, 5))

    add([""] * COLS, 16)
    fmt(row_index() - 1, row_index(), 0, COLS, bg=PAPER)

    # динамика
    r = add([report.series_title] + [""] * 5, 28)
    merge(r)
    fmt(r, r + 1, 0, COLS, bg=NAVY_SOFT, fg=WHITE, size=12, bold=True, h="LEFT", indent=1)

    r = add(list(report.series_headers) + ["", ""], 26)
    fmt(r, r + 1, 0, 4, bg=NAVY, fg=WHITE, size=9, bold=True, h="CENTER")
    fmt(r, r + 1, 4, COLS, bg=NAVY)

    extra_is_money = report.params.report_type in {"Продажи", "Финансы"}
    extra_is_nps = report.params.report_type == "Клиенты"
    series_start = row_index()
    for i, point in enumerate(report.series):
        r = add([point.label, point.amount, point.volume, point.extra, "", ""], 22)
        bg = PAPER if i % 2 == 0 else ALT
        fmt(r, r + 1, 0, 1, bg=bg, fg=TEXT, size=10, h="LEFT", indent=1)
        fmt(r, r + 1, 1, 2, bg=bg, fg=TEXT, size=10, h="RIGHT", number='#,##0" ₽"')
        fmt(r, r + 1, 2, 3, bg=bg, fg=TEXT, size=10, h="CENTER", number="#,##0")
        if extra_is_nps:
            number = "0.0"
        elif extra_is_money:
            number = '#,##0" ₽"'
        else:
            number = "0.0"
        fmt(r, r + 1, 3, 4, bg=bg, fg=TEXT, size=10, h="RIGHT", number=number)
        fmt(r, r + 1, 4, COLS, bg=bg)
    series_end = row_index()
    formats.append(_outer_border(series_start - 1, series_end, 0, 4))

    add([""] * COLS, 16)
    fmt(row_index() - 1, row_index(), 0, COLS, bg=PAPER)

    r = add(["4. Выводы"] + [""] * 5, 28)
    merge(r)
    fmt(r, r + 1, 0, COLS, bg=NAVY_SOFT, fg=WHITE, size=12, bold=True, h="LEFT", indent=1)

    r = add([report.conclusion] + [""] * 5, 78)
    merge(r)
    fmt(r, r + 1, 0, COLS, bg=PAPER, fg=TEXT, size=10, h="LEFT", v="TOP", wrap=True, indent=1)

    if report.extra_notes:
        r = add(["Комментарий составителя"] + [""] * 5, 22)
        merge(r)
        fmt(r, r + 1, 0, COLS, bg=CREAM, fg=MUTED, size=9, bold=True, italic=True, indent=1)
        r = add([report.extra_notes] + [""] * 5, 48)
        merge(r)
        fmt(r, r + 1, 0, COLS, bg=CREAM, fg=TEXT, size=10, wrap=True, v="TOP", indent=1)

    add([""] * COLS, 18)
    fmt(row_index() - 1, row_index(), 0, COLS, bg=PAPER)

    r = add(
        [
            f"Ответственный: {p.author}",
            "",
            "",
            "Руководитель: ____________________",
            "",
            "",
        ],
        26,
    )
    merge(r, 0, 3)
    merge(r, 3, COLS)
    fmt(r, r + 1, 0, 3, bg=PAPER, fg=TEXT, size=10)
    fmt(r, r + 1, 3, COLS, bg=PAPER, fg=TEXT, size=10)

    r = add(
        [
            f"Дата: {report.generated_at:%d.%m.%Y}",
            "",
            "",
            "М.П.",
            "",
            "",
        ],
        22,
    )
    merge(r, 0, 3)
    merge(r, 3, COLS)
    fmt(r, r + 1, 0, COLS, bg=PAPER, fg=MUTED, size=9)

    add([""] * COLS, 10)
    r = add(
        ["Документ сформирован автоматически. Данные симулированы для демонстрации EXELIO."]
        + [""] * 5,
        20,
    )
    merge(r)
    fmt(r, r + 1, 0, COLS, bg=NAVY, fg=GOLD, size=8, italic=True, h="CENTER")

    last_row = len(values)
    # бумага на всех ещё не закрашенных промежутках уже проставлена построчно
    return values, merges, formats, heights, last_row


def _sheet_setup(sheet_id: int, row_count: int) -> list[dict[str, Any]]:
    return [
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"hideGridlines": True, "rowCount": row_count},
                    "tabColor": rgb(GOLD),
                },
                "fields": "gridProperties.hideGridlines,gridProperties.rowCount,tabColor",
            }
        },
        _repeat(0, row_count, 0, COLS, bg=CREAM, fg=TEXT, size=10, font="Calibri"),
    ]


def _column_widths(sheet_id: int) -> list[dict[str, Any]]:
    widths = (220, 130, 140, 150, 160, 40)
    requests = []
    for index, width in enumerate(widths):
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": index,
                        "endIndex": index + 1,
                    },
                    "properties": {"pixelSize": width},
                    "fields": "pixelSize",
                }
            }
        )
    return requests


def _row_heights(sheet_id: int, heights: list[int]) -> list[dict[str, Any]]:
    requests = []
    for index, height in enumerate(heights):
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": index,
                        "endIndex": index + 1,
                    },
                    "properties": {"pixelSize": height},
                    "fields": "pixelSize",
                }
            }
        )
    return requests


def _merge(r0: int, r1: int, c0: int, c1: int) -> dict[str, Any]:
    return {
        "mergeCells": {
            "range": {
                "sheetId": None,  # заполняется в _bind
                "startRowIndex": r0,
                "endRowIndex": r1,
                "startColumnIndex": c0,
                "endColumnIndex": c1,
            },
            "mergeType": "MERGE_ALL",
        }
    }


def _repeat(
    r0: int,
    r1: int,
    c0: int,
    c1: int,
    *,
    bg: str | None = None,
    fg: str | None = None,
    size: int | None = None,
    bold: bool = False,
    italic: bool = False,
    h: str | None = None,
    v: str = "MIDDLE",
    wrap: bool = False,
    font: str = "Calibri",
    number: str | None = None,
    indent: int | None = None,
    bottom: str | None = None,
    bottom_w: int = 1,
) -> dict[str, Any]:
    cell_format: dict[str, Any] = {"verticalAlignment": v}
    fields = ["userEnteredFormat.verticalAlignment"]
    if bg:
        cell_format["backgroundColor"] = rgb(bg)
        fields.append("userEnteredFormat.backgroundColor")
    if h:
        cell_format["horizontalAlignment"] = h
        fields.append("userEnteredFormat.horizontalAlignment")
    if wrap:
        cell_format["wrapStrategy"] = "WRAP"
        fields.append("userEnteredFormat.wrapStrategy")
    if indent:
        cell_format["padding"] = {"left": indent * 8}
        fields.append("userEnteredFormat.padding")
    text_format: dict[str, Any] = {"fontFamily": font}
    fields.append("userEnteredFormat.textFormat.fontFamily")
    if fg:
        text_format["foregroundColor"] = rgb(fg)
        fields.append("userEnteredFormat.textFormat.foregroundColor")
    if size is not None:
        text_format["fontSize"] = size
        fields.append("userEnteredFormat.textFormat.fontSize")
    if bold:
        text_format["bold"] = True
        fields.append("userEnteredFormat.textFormat.bold")
    if italic:
        text_format["italic"] = True
        fields.append("userEnteredFormat.textFormat.italic")
    cell_format["textFormat"] = text_format
    if number:
        cell_format["numberFormat"] = {"type": "NUMBER", "pattern": number}
        fields.append("userEnteredFormat.numberFormat")
    if bottom:
        cell_format["borders"] = {
            "bottom": {"style": "SOLID", "width": bottom_w, "color": rgb(bottom)}
        }
        fields.append("userEnteredFormat.borders.bottom")

    return {
        "repeatCell": {
            "range": {
                "sheetId": None,
                "startRowIndex": r0,
                "endRowIndex": r1,
                "startColumnIndex": c0,
                "endColumnIndex": c1,
            },
            "cell": {"userEnteredFormat": cell_format},
            "fields": ",".join(fields),
        }
    }


def _outer_border(r0: int, r1: int, c0: int, c1: int) -> dict[str, Any]:
    return {
        "updateBorders": {
            "range": {
                "sheetId": None,
                "startRowIndex": r0,
                "endRowIndex": r1,
                "startColumnIndex": c0,
                "endColumnIndex": c1,
            },
            "top": {"style": "SOLID", "width": 1, "color": rgb(NAVY)},
            "bottom": {"style": "SOLID", "width": 1, "color": rgb(NAVY)},
            "left": {"style": "SOLID", "width": 1, "color": rgb(NAVY)},
            "right": {"style": "SOLID", "width": 1, "color": rgb(NAVY)},
        }
    }


def _bind_sheet_id(requests: list[dict[str, Any]], sheet_id: int) -> list[dict[str, Any]]:
    for item in requests:
        for key in ("mergeCells", "repeatCell", "updateBorders"):
            if key in item and "range" in item[key]:
                if item[key]["range"].get("sheetId") is None:
                    item[key]["range"]["sheetId"] = sheet_id
    return requests


def write_report(client: GoogleSheetsClient, report: SimulatedReport) -> str:
    """Создаёт новый лист-документ и возвращает URL."""
    stamp = report.generated_at.strftime("%d.%m.%Y %H-%M")
    base_title = f"{report.params.report_type} {stamp}"
    title = client.unique_sheet_title(base_title)

    values, merges, formats, heights, last_row = _compose(report)
    row_count = max(last_row + 8, 80)
    sheet_id = client.create_sheet(
        title,
        row_count=row_count,
        column_count=COLS,
        switch=True,
    )

    requests = _bind_sheet_id(
        _sheet_setup(sheet_id, row_count)
        + _column_widths(sheet_id)
        + _row_heights(sheet_id, heights)
        + merges
        + formats,
        sheet_id,
    )
    client.write(f"A1:F{last_row}", values, value_input_option="USER_ENTERED")
    client.batch_update(requests)
    return client.sheet_url(sheet_id)
