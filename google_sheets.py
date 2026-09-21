"""
Переиспользуемый CRUD-клиент для Google Sheets через Service Account.

Пример подключения в другом приложении:

    from google_sheets import GoogleSheetsClient

    sheets = GoogleSheetsClient(
        credentials_path="excel-factory-509306-5ae95b8dd439.json",
        spreadsheet_id="Your Spreadsheet ID",
    )
    rows = sheets.read_all()
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Sequence

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)

# Путь к JSON-ключу по умолчанию — рядом с этим модулем
DEFAULT_CREDENTIALS_PATH = Path(__file__).resolve().parent / (
    "excel-factory-509306-5ae95b8dd439.json"
)


class GoogleSheetsError(RuntimeError):
    """Ошибка при работе с Google Sheets API."""


class GoogleSheetsClient:
    """CRUD-обёртка над Google Sheets API (service account)."""

    def __init__(
        self,
        spreadsheet_id: str,
        credentials_path: str | Path | None = None,
        *,
        sheet_name: str | None = None,
    ) -> None:
        if not spreadsheet_id:
            raise ValueError("spreadsheet_id обязателен")

        self.spreadsheet_id = spreadsheet_id
        self.credentials_path = Path(
            credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH") or DEFAULT_CREDENTIALS_PATH
        )

        if not self.credentials_path.is_file():
            raise FileNotFoundError(
                f"JSON-ключ сервисного аккаунта не найден: {self.credentials_path}"
            )

        credentials = Credentials.from_service_account_file(
            str(self.credentials_path),
            scopes=SCOPES,
        )
        self._service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        self._sheets = self._service.spreadsheets()

        # None / пусто — берём первый лист таблицы (часто «Лист1», не Sheet1)
        self.sheet_name = sheet_name.strip() if sheet_name else self.list_sheet_names()[0]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _quote_sheet(name: str) -> str:
        """Экранирует имя листа для A1-нотации."""
        escaped = name.replace("'", "''")
        return f"'{escaped}'"

    def _a1(self, range_a1: str | None = None) -> str:
        """Собирает A1-диапазон с именем листа, если его ещё нет."""
        sheet = self._quote_sheet(self.sheet_name)
        if range_a1 is None or range_a1.strip() == "":
            return sheet
        if "!" in range_a1:
            return range_a1
        return f"{sheet}!{range_a1}"

    def _request(self, call: Any) -> Any:
        try:
            return call.execute()
        except HttpError as exc:
            raise GoogleSheetsError(f"Google Sheets API error: {exc}") from exc

    def list_sheet_names(self) -> list[str]:
        """Возвращает названия всех листов таблицы."""
        meta = self._request(
            self._sheets.get(
                spreadsheetId=self.spreadsheet_id,
                fields="sheets.properties.title",
            )
        )
        names = [
            sheet["properties"]["title"]
            for sheet in meta.get("sheets", [])
            if "title" in sheet.get("properties", {})
        ]
        if not names:
            raise GoogleSheetsError("В таблице нет листов")
        return names

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def read(
        self,
        range_a1: str | None = None,
        *,
        value_render_option: str = "FORMATTED_VALUE",
    ) -> list[list[Any]]:
        """Читает значения из диапазона. Без range_a1 — весь лист."""
        result = self._request(
            self._sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=self._a1(range_a1),
                valueRenderOption=value_render_option,
            )
        )
        return result.get("values", [])

    def read_all(self) -> list[list[Any]]:
        """Читает все заполненные ячейки активного листа."""
        return self.read()

    def read_cell(self, cell: str) -> Any | None:
        """Читает одну ячейку, например 'A1'."""
        values = self.read(cell)
        if not values or not values[0]:
            return None
        return values[0][0]

    # ------------------------------------------------------------------
    # CREATE / UPDATE (write)
    # ------------------------------------------------------------------

    def write(
        self,
        range_a1: str,
        values: Sequence[Sequence[Any]],
        *,
        value_input_option: str = "USER_ENTERED",
    ) -> dict[str, Any]:
        """Записывает (перезаписывает) значения в указанный диапазон."""
        body = {"values": [list(row) for row in values]}
        return self._request(
            self._sheets.values().update(
                spreadsheetId=self.spreadsheet_id,
                range=self._a1(range_a1),
                valueInputOption=value_input_option,
                body=body,
            )
        )

    def write_cell(
        self,
        cell: str,
        value: Any,
        *,
        value_input_option: str = "USER_ENTERED",
    ) -> dict[str, Any]:
        """Записывает значение в одну ячейку."""
        return self.write(cell, [[value]], value_input_option=value_input_option)

    def append(
        self,
        values: Sequence[Sequence[Any]],
        *,
        range_a1: str | None = None,
        value_input_option: str = "USER_ENTERED",
        insert_data_option: str = "INSERT_ROWS",
    ) -> dict[str, Any]:
        """Добавляет строки в конец таблицы (CREATE)."""
        body = {"values": [list(row) for row in values]}
        return self._request(
            self._sheets.values().append(
                spreadsheetId=self.spreadsheet_id,
                range=self._a1(range_a1),
                valueInputOption=value_input_option,
                insertDataOption=insert_data_option,
                body=body,
            )
        )

    def update(
        self,
        range_a1: str,
        values: Sequence[Sequence[Any]],
        *,
        value_input_option: str = "USER_ENTERED",
    ) -> dict[str, Any]:
        """Алиас write — обновление существующих ячеек (UPDATE)."""
        return self.write(range_a1, values, value_input_option=value_input_option)

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def clear(self, range_a1: str | None = None) -> dict[str, Any]:
        """Очищает значения в диапазоне (DELETE содержимого). Без range — весь лист."""
        return self._request(
            self._sheets.values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=self._a1(range_a1),
                body={},
            )
        )

    def delete_rows(
        self,
        start_index: int,
        end_index: int,
        *,
        sheet_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Удаляет строки по индексам (0-based, end не включительно).

        start_index=0, end_index=1 — удалить первую строку листа.
        """
        if start_index < 0 or end_index <= start_index:
            raise ValueError("Нужно: 0 <= start_index < end_index")

        resolved_sheet_id = sheet_id if sheet_id is not None else self._resolve_sheet_id()
        body = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": resolved_sheet_id,
                            "dimension": "ROWS",
                            "startIndex": start_index,
                            "endIndex": end_index,
                        }
                    }
                }
            ]
        }
        return self._request(
            self._sheets.batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body,
            )
        )

    def _resolve_sheet_id(self) -> int:
        meta = self._request(
            self._sheets.get(
                spreadsheetId=self.spreadsheet_id,
                fields="sheets.properties",
            )
        )
        for sheet in meta.get("sheets", []):
            props = sheet.get("properties", {})
            if props.get("title") == self.sheet_name:
                return int(props["sheetId"])
        raise GoogleSheetsError(f"Лист не найден: {self.sheet_name!r}")

    def get_sheet_id(self) -> int:
        """ID активного листа (нужен для форматирования и merge)."""
        return self._resolve_sheet_id()

    def sheet_url(self, sheet_id: int | None = None) -> str:
        """Ссылка на таблицу с якорем на лист."""
        gid = sheet_id if sheet_id is not None else self.get_sheet_id()
        return (
            f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit#gid={gid}"
        )

    def batch_update(self, requests: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Низкоуровневый spreadsheets.batchUpdate (стиль, merge, размеры)."""
        if not requests:
            return {}
        return self._request(
            self._sheets.batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": list(requests)},
            )
        )

    def unique_sheet_title(self, base: str) -> str:
        """Подбирает имя листа, которого ещё нет в книге."""
        cleaned = _safe_sheet_title(base)
        existing = set(self.list_sheet_names())
        if cleaned not in existing:
            return cleaned
        for index in range(2, 80):
            suffix = f" ({index})"
            candidate = _safe_sheet_title(cleaned[: 100 - len(suffix)] + suffix)
            if candidate not in existing:
                return candidate
        raise GoogleSheetsError(f"Не удалось подобрать имя листа: {base}")

    def create_sheet(
        self,
        title: str,
        *,
        row_count: int = 160,
        column_count: int = 8,
        switch: bool = True,
    ) -> int:
        """Создаёт лист и (по умолчанию) делает его активным. Возвращает sheetId."""
        safe_title = _safe_sheet_title(title)
        result = self.batch_update(
            [
                {
                    "addSheet": {
                        "properties": {
                            "title": safe_title,
                            "gridProperties": {
                                "rowCount": row_count,
                                "columnCount": column_count,
                            },
                        }
                    }
                }
            ]
        )
        replies = result.get("replies") or [{}]
        sheet_id = int(replies[0]["addSheet"]["properties"]["sheetId"])
        if switch:
            self.sheet_name = safe_title
        return sheet_id


def _safe_sheet_title(title: str) -> str:
    """Имена листов Google: без : \\ / ? * [ ], не длиннее 100 символов."""
    forbidden = str.maketrans({ch: "-" for ch in r":\/?*[]"})
    cleaned = title.translate(forbidden).strip() or "Лист"
    return cleaned[:100]


DEFAULT_SPREADSHEET_ID = "1GDK_tx2YUEbh8tVmwpXnB3fcREEkRoXgR6Chm4A5KM4"


def main() -> None:
    """Точка входа: читает все ячейки и печатает их в консоль."""
    spreadsheet_id = (
        os.getenv("SPREADSHEET_ID", "").strip() or DEFAULT_SPREADSHEET_ID
    )
    # Пусто → клиент сам возьмёт первый лист (Лист1 / Sheet1 / …)
    sheet_name = os.getenv("SHEET_NAME", "").strip() or None
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH") or str(DEFAULT_CREDENTIALS_PATH)

    client = GoogleSheetsClient(
        spreadsheet_id=spreadsheet_id,
        credentials_path=credentials_path,
        sheet_name=sheet_name,
    )

    rows = client.read_all()
    if not rows:
        _safe_print(f"Лист: {client.sheet_name} | (таблица пуста)")
        return

    _safe_print(f"Лист: {client.sheet_name} | строк: {len(rows)}")
    for i, row in enumerate(rows, start=1):
        _safe_print(f"{i}: {row}")


def _safe_print(text: str) -> None:
    """Печать без падения на символах вроде ₽ в cp1251-консоли."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


if __name__ == "__main__":
    main()
