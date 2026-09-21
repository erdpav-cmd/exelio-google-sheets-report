"""Симуляция случайных аналитических отчётов по параметрам формы."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Sequence


DEPARTMENTS = ("Продажи", "Розница", "Опт", "Маркетинг", "Клиентский сервис")
REGIONS = ("Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Вся сеть")
REPORT_TYPES = ("Продажи", "Остатки", "Финансы", "Клиенты")


@dataclass(frozen=True)
class ReportParams:
    date_from: date
    date_to: date
    report_type: str
    department: str
    region: str
    author: str
    notes: str = ""


@dataclass(frozen=True)
class CategoryRow:
    name: str
    quantity: int
    amount: float
    share: float
    change: float


@dataclass(frozen=True)
class SeriesPoint:
    label: str
    amount: float
    volume: int
    extra: float


@dataclass
class SimulatedReport:
    params: ReportParams
    report_no: str
    generated_at: datetime
    title: str
    kpis: list[tuple[str, str, str]]  # (название, значение, подпись)
    table_title: str
    table_headers: tuple[str, str, str, str, str]
    categories: list[CategoryRow]
    series_title: str
    series_headers: tuple[str, str, str, str]
    series: list[SeriesPoint]
    total_amount: float
    total_volume: int
    conclusion: str
    extra_notes: str = ""
    highlights: list[str] = field(default_factory=list)


_TEMPLATES: dict[str, dict] = {
    "Продажи": {
        "title": "ОТЧЁТ О ПРОДАЖАХ",
        "categories": (
            "Электроника",
            "Бытовая техника",
            "Одежда и обувь",
            "Продукты",
            "Косметика",
            "Спорт и отдых",
        ),
        "table_title": "2. Структура продаж по категориям",
        "table_headers": ("Категория", "Единиц", "Выручка, ₽", "Доля", "Δ к пред. периоду"),
        "series_title": "3. Динамика выручки",
        "series_headers": ("Период", "Выручка, ₽", "Заказы", "Средний чек, ₽"),
        "kpi_labels": ("Выручка", "Заказы", "Средний чек", "Конверсия"),
    },
    "Остатки": {
        "title": "ОТЧЁТ ПО ТОВАРНЫМ ОСТАТКАМ",
        "categories": (
            "Склад А — центр",
            "Склад Б — юг",
            "Склад В — восток",
            "Фулфилмент",
            "Транзит",
            "Брак / резерв",
        ),
        "table_title": "2. Распределение остатков",
        "table_headers": ("Площадка", "SKU", "Стоимость, ₽", "Доля", "Δ к пред. периоду"),
        "series_title": "3. Движение склада",
        "series_headers": ("Период", "Стоимость, ₽", "Приход, шт.", "Оборачиваемость"),
        "kpi_labels": ("Стоимость склада", "Позиций SKU", "Оборачиваемость", "Доля неликвида"),
    },
    "Финансы": {
        "title": "ФИНАНСОВЫЙ ОТЧЁТ",
        "categories": (
            "Выручка",
            "Себестоимость",
            "Операционные расходы",
            "Маркетинг",
            "Фонд оплаты труда",
            "Прочие доходы/расходы",
        ),
        "table_title": "2. Структура P&L",
        "table_headers": ("Статья", "Проводок", "Сумма, ₽", "Доля", "Δ к пред. периоду"),
        "series_title": "3. Динамика денежного потока",
        "series_headers": ("Период", "Поступления, ₽", "Платежи", "Чистый поток, ₽"),
        "kpi_labels": ("Выручка", "Валовая прибыль", "Маржа", "EBITDA"),
    },
    "Клиенты": {
        "title": "ОТЧЁТ ПО КЛИЕНТСКОЙ БАЗЕ",
        "categories": (
            "Новые клиенты",
            "Повторные покупки",
            "VIP / лояльность",
            "Корпоративный канал",
            "Маркетплейсы",
            "Неактивные 90+ дней",
        ),
        "table_title": "2. Сегменты клиентской базы",
        "table_headers": ("Сегмент", "Клиентов", "LTV, ₽", "Доля", "Δ к пред. периоду"),
        "series_title": "3. Динамика привлечения",
        "series_headers": ("Период", "Выручка, ₽", "Новые клиенты", "NPS"),
        "kpi_labels": ("Активные клиенты", "Новые", "NPS", "Повторные покупки"),
    },
}


def simulate_report(params: ReportParams, *, rng: random.Random | None = None) -> SimulatedReport:
    if params.date_to < params.date_from:
        raise ValueError("Дата «по» не может быть раньше даты «с»")

    rng = rng or random.Random()
    kind = params.report_type if params.report_type in _TEMPLATES else "Продажи"
    tmpl = _TEMPLATES[kind]
    days = (params.date_to - params.date_from).days + 1
    scale = max(days, 7)

    names: Sequence[str] = tmpl["categories"]
    weights = [rng.uniform(0.08, 1.0) for _ in names]
    weight_sum = sum(weights)

    if kind == "Остатки":
        total_amount = rng.uniform(18_000_000, 95_000_000) * (scale / 30)
        total_volume = int(rng.uniform(4_000, 18_000))
    elif kind == "Финансы":
        total_amount = rng.uniform(8_000_000, 42_000_000) * (scale / 30)
        total_volume = int(rng.uniform(120, 680))
    elif kind == "Клиенты":
        total_amount = rng.uniform(3_500_000, 28_000_000) * (scale / 30)
        total_volume = int(rng.uniform(800, 9_500))
    else:
        total_amount = rng.uniform(2_400_000, 18_500_000) * (scale / 30)
        total_volume = int(rng.uniform(180, 2_400) * (scale / 14))

    categories: list[CategoryRow] = []
    for name, weight in zip(names, weights):
        share = weight / weight_sum
        amount = round(total_amount * share, 2)
        qty = max(1, int(total_volume * share * rng.uniform(0.75, 1.25)))
        change = rng.uniform(-0.18, 0.32)
        categories.append(CategoryRow(name, qty, amount, share, change))

    categories.sort(key=lambda row: row.amount, reverse=True)
    total_amount = round(sum(row.amount for row in categories), 2)
    total_volume = sum(row.quantity for row in categories)
    for i, row in enumerate(categories):
        categories[i] = CategoryRow(
            row.name,
            row.quantity,
            row.amount,
            row.amount / total_amount if total_amount else 0,
            row.change,
        )

    series = _build_series(params.date_from, params.date_to, total_amount, total_volume, kind, rng)
    kpis = _build_kpis(kind, tmpl["kpi_labels"], total_amount, total_volume, categories, rng)
    conclusion, highlights = _build_text(params, kind, total_amount, total_volume, categories, kpis)

    stamp = datetime.now()
    report_no = f"ОТЧ-{stamp:%Y%m%d}-{rng.randint(1000, 9999)}"
    extra = params.notes.strip()

    return SimulatedReport(
        params=params,
        report_no=report_no,
        generated_at=stamp,
        title=tmpl["title"],
        kpis=kpis,
        table_title=tmpl["table_title"],
        table_headers=tmpl["table_headers"],
        categories=categories,
        series_title=tmpl["series_title"],
        series_headers=tmpl["series_headers"],
        series=series,
        total_amount=total_amount,
        total_volume=total_volume,
        conclusion=conclusion,
        extra_notes=extra,
        highlights=highlights,
    )


def _build_series(
    date_from: date,
    date_to: date,
    total_amount: float,
    total_volume: int,
    kind: str,
    rng: random.Random,
) -> list[SeriesPoint]:
    days = (date_to - date_from).days + 1
    if days <= 16:
        labels = [(date_from + timedelta(days=i)).strftime("%d.%m.%Y") for i in range(days)]
    elif days <= 90:
        labels = []
        cursor = date_from
        while cursor <= date_to:
            week_end = min(cursor + timedelta(days=6), date_to)
            labels.append(f"{cursor:%d.%m}–{week_end:%d.%m}")
            cursor = week_end + timedelta(days=1)
    else:
        labels = []
        months_ru = (
            "янв", "фев", "мар", "апр", "май", "июн",
            "июл", "авг", "сен", "окт", "ноя", "дек",
        )
        year, month = date_from.year, date_from.month
        while (year, month) <= (date_to.year, date_to.month):
            labels.append(f"{months_ru[month - 1]} {year}")
            if month == 12:
                year, month = year + 1, 1
            else:
                month += 1

    n = len(labels)
    raw = [rng.uniform(0.45, 1.35) for _ in range(n)]
    # лёгкий тренд
    for i in range(n):
        raw[i] *= 0.85 + 0.3 * (i / max(n - 1, 1))
    s = sum(raw)
    points: list[SeriesPoint] = []
    for i, label in enumerate(labels):
        amount = round(total_amount * raw[i] / s, 2)
        volume = max(1, int(total_volume * raw[i] / s))
        if kind == "Клиенты":
            extra = round(rng.uniform(28, 72), 1)
        elif kind == "Остатки":
            extra = round(rng.uniform(2.1, 8.4), 1)
        elif kind == "Финансы":
            extra = round(amount * rng.uniform(-0.12, 0.22), 2)
        else:
            extra = round(amount / volume, 2) if volume else 0
        points.append(SeriesPoint(label, amount, volume, extra))
    return points


def _build_kpis(
    kind: str,
    labels: tuple[str, ...],
    total_amount: float,
    total_volume: int,
    categories: list[CategoryRow],
    rng: random.Random,
) -> list[tuple[str, str, str]]:
    avg_change = sum(row.change for row in categories) / len(categories)
    arrow = "▲" if avg_change >= 0 else "▼"
    change_txt = f"{arrow} {abs(avg_change) * 100:.1f}% к пред. периоду"

    if kind == "Остатки":
        sku = total_volume
        turnover = rng.uniform(2.4, 7.8)
        illiquid = rng.uniform(0.04, 0.16)
        return [
            (labels[0], _money(total_amount), change_txt),
            (labels[1], f"{sku:,}".replace(",", " "), "на всех площадках"),
            (labels[2], f"{turnover:.1f}x", "оборотов за период"),
            (labels[3], f"{illiquid * 100:.1f}%", "требует внимания"),
        ]
    if kind == "Финансы":
        cogs_share = rng.uniform(0.52, 0.68)
        gross = total_amount * (1 - cogs_share)
        margin = gross / total_amount if total_amount else 0
        ebitda = gross * rng.uniform(0.18, 0.42)
        return [
            (labels[0], _money(total_amount), change_txt),
            (labels[1], _money(gross), f"доля {margin * 100:.1f}%"),
            (labels[2], f"{margin * 100:.1f}%", "валовая маржа"),
            (labels[3], _money(ebitda), "операционный результат"),
        ]
    if kind == "Клиенты":
        active = total_volume
        new = int(active * rng.uniform(0.12, 0.34))
        nps = rng.uniform(32, 74)
        repeat = rng.uniform(0.28, 0.61)
        return [
            (labels[0], f"{active:,}".replace(",", " "), change_txt),
            (labels[1], f"{new:,}".replace(",", " "), "за выбранный период"),
            (labels[2], f"{nps:.0f}", "индекс лояльности"),
            (labels[3], f"{repeat * 100:.1f}%", "доля повторных"),
        ]

    orders = total_volume
    avg_check = total_amount / orders if orders else 0
    conversion = rng.uniform(0.018, 0.067)
    return [
        (labels[0], _money(total_amount), change_txt),
        (labels[1], f"{orders:,}".replace(",", " "), "оформленных заказов"),
        (labels[2], _money(avg_check), "на один заказ"),
        (labels[3], f"{conversion * 100:.1f}%", "визиты → покупка"),
    ]


def _build_text(
    params: ReportParams,
    kind: str,
    total_amount: float,
    total_volume: int,
    categories: list[CategoryRow],
    kpis: list[tuple[str, str, str]],
) -> tuple[str, list[str]]:
    top = categories[0]
    weak = min(categories, key=lambda row: row.change)
    period = f"{params.date_from:%d.%m.%Y} — {params.date_to:%d.%m.%Y}"
    verb = {
        "Продажи": "сформировало продажи",
        "Остатки": "фиксирует товарный запас",
        "Финансы": "отражает финансовый результат",
        "Клиенты": "обслужило клиентскую базу",
    }.get(kind, "сформировало показатели")

    conclusion = (
        f"За период {period} подразделение «{params.department}» в регионе "
        f"«{params.region}» {verb} на уровне { _money(total_amount) } "
        f"({total_volume:,} ед.). ".replace(",", " ")
        + f"Ключевой вклад даёт «{top.name}» — {top.share * 100:.1f}% структуры "
        f"(динамика {top.change * 100:+.1f}%). "
        f"Зона внимания — «{weak.name}» ({weak.change * 100:+.1f}% к предыдущему периоду). "
        f"Отчёт подготовлен автоматически по симулированным данным и носит демонстрационный характер."
    )
    highlights = [
        f"{kpis[0][0]}: {kpis[0][1]}",
        f"Лидер: {top.name} ({top.share * 100:.0f}%)",
        f"Риск: {weak.name}",
        f"Ответственный: {params.author}",
    ]
    return conclusion, highlights


def _money(value: float) -> str:
    text = f"{value:,.0f}".replace(",", " ")
    return f"{text} ₽"


def parse_ru_date(text: str) -> date:
    raw = text.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Некорректная дата: {text!r}. Ожидается ДД.ММ.ГГГГ")
