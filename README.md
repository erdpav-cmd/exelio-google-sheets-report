# EXELIO — автоматические отчёты в Google Таблицах

> Python-приложение, которое превращает параметры в готовый оформленный документ в Google Sheets.

В Tkinter задаёте период и пару полей, программа **симулирует** аналитический отчёт и записывает его в Google Таблицу как оформленный документ (шапка, KPI, таблицы, выводы), а не как сырой список ячеек.

## 🎯 Возможности

- GUI с календарём и валидацией (Tkinter)
- 4 типа отчётов: продажи, остатки, финансы, клиенты — по периоду, подразделению и региону
- Автоматическое создание нового листа с шапкой, KPI-блоками, таблицами и выводами (без сетки)
- Переиспользуемый CRUD-клиент Google Sheets API с OOP (`GoogleSheetsClient`: чтение, добавление, обновление и очистка ячеек)
- Работа с приватными таблицами через сервисный аккаунт
- Threading для отзывчивого GUI
- Обработка ошибок `GoogleSheetsError`

## 📸 Скриншоты

<img src="screenshots/gui-form.png" width="480">
<img src="screenshots/gui-success.png" width="480">
<img src="screenshots/sheets-report.png" width="480">

## 🚀 Установка

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка

1. JSON-ключ сервисного аккаунта лежит в корне проекта.
2. В Google Таблице выдайте доступ на **редактирование** email'у сервисного аккаунта (`client_email` из JSON).
3. ID таблицы по умолчанию уже прописан. При необходимости:

```powershell
$env:SPREADSHEET_ID = "ваш_id_таблицы"
$env:GOOGLE_CREDENTIALS_PATH = "excel-factory-509306-5ae95b8dd439.json"
```

## 🔐 Переменные окружения

| Переменная | Описание |
|------------|----------|
| `SPREADSHEET_ID` | ID Google Таблицы |
| `SHEET_NAME` | Имя листа для `google_sheets.py` (иначе — первый лист) |
| `GOOGLE_CREDENTIALS_PATH` | Путь к JSON-ключу |

## Запуск приложения

```bash
python app.py
```

В форме укажите:

- период **с / по**
- тип отчёта (продажи, остатки, финансы, клиенты)
- подразделение и регион
- ответственного и необязательный комментарий

После кнопки «Сформировать» появится **новый лист** в таблице: без сетки, с шапкой, блоками показателей и таблицами.

## Проверка клиента таблиц

```bash
python google_sheets.py
```

Печатает содержимое активного листа в консоль.

## Использование клиента в коде

```python
from google_sheets import GoogleSheetsClient

sheets = GoogleSheetsClient(
    spreadsheet_id="YOUR_SPREADSHEET_ID",
    credentials_path="excel-factory-509306-5ae95b8dd439.json",
)

rows = sheets.read_all()
sheets.append([["имя", "email", "статус"]])
sheets.update("A2:C2", [["Иван", "ivan@example.com", "ok"]])
sheets.clear("A2:D2")
```

## 🏗 Архитектура

| Файл | Назначение |
|------|------------|
| `app.py` | GUI с кастомным `DateField` и потоковой работой |
| `report_data.py` | Симуляция аналитических показателей |
| `report_writer.py` | Вёрстка документа через `batchUpdate` |
| `google_sheets.py` | Переиспользуемый CRUD-клиент Sheets API |
| `requirements.txt` | Зависимости |
| `*.json` | Ключ сервисного аккаунта (не коммитить) |

## 💼 Применение в бизнесе

- Автоматические отчёты по продажам из CRM
- Ежедневные сводки из 1С / ERP
- Выгрузка аналитики рекламных кампаний
- Финансовые отчёты для руководства

## 🛠 Стек

Python 3.12 · Tkinter · google-api-python-client · Google Sheets API v4 · Service Account

## 👤 Автор

Павел Эрдниев

- Telegram: [@Erdpav](https://t.me/Erdpav)
- GitHub: [erdpav-cmd](https://github.com/erdpav-cmd)
- Специализация: Python-разработчик, LLM-интеграции, автоматизация бизнес-процессов
