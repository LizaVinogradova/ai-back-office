from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

import pandas as pd


MONTH_ALIASES = {
    "jan": "Январь",
    "feb": "Февраль",
    "mar": "Март",
    "apr": "Апрель",
    "may": "Май",
    "jun": "Июнь",
    "jul": "Июль",
    "aug": "Август",
    "sep": "Сентябрь",
    "oct": "Октябрь",
    "nov": "Ноябрь",
    "dec": "Декабрь",
}


def clean(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return value


def fmt(value: Any, suffix: str = "") -> str:
    value = clean(value)
    if value == "":
        return ""
    if isinstance(value, float):
        text = f"{value:.1f}" if not value.is_integer() else f"{int(value)}"
    else:
        text = str(value)
    return f"{text}{suffix}"


def fmt_delta(value: Any, suffix: str = "") -> str:
    value = clean(value)
    if value == "":
        return ""
    if isinstance(value, (int, float)):
        sign = "+" if value > 0 else ""
        return f"{sign}{value:.1f}{suffix}"
    return str(value)


def normalize_period(value: str) -> str:
    value = value.strip()
    parts = value.split()
    if len(parts) == 2 and parts[0].lower()[:3] in MONTH_ALIASES:
        return f"{MONTH_ALIASES[parts[0].lower()[:3]]} {parts[1]}"
    return value


def find_sheet(sheets: dict[str, pd.DataFrame], prefix: str) -> str:
    for name in sheets:
        if name.startswith(prefix):
            return name
    raise ValueError(f"Не найден лист, начинающийся с {prefix!r}")


def read_workbook(path: Path) -> dict[str, pd.DataFrame]:
    return pd.read_excel(path, sheet_name=None)


def month_columns(columns: list[str]) -> list[str]:
    return [
        col
        for col in columns
        if isinstance(col, str)
        and col != "Статья"
        and "YTD" not in col
        and any(month in col for month in MONTH_ALIASES.values())
    ]


def latest_period(pl: pd.DataFrame) -> str:
    months = month_columns(list(pl.columns))
    if not months:
        raise ValueError("Не найдены месячные колонки в P&L")
    for col in reversed(months):
        values = pl[col].dropna()
        if not values.empty:
            return col
    raise ValueError("Не найдены заполненные месячные колонки в P&L")


def previous_period(pl: pd.DataFrame, period: str) -> str | None:
    months = month_columns(list(pl.columns))
    if period not in months:
        raise ValueError(f"Период {period!r} не найден в P&L. Доступно: {', '.join(months)}")
    index = months.index(period)
    return months[index - 1] if index > 0 else None


def section_rows(pl: pd.DataFrame, start_label: str, total_label: str) -> pd.DataFrame:
    start_idx = pl.index[pl["Статья"] == start_label][0] + 1
    total_idx = pl.index[pl["Статья"] == total_label][0]
    return pl.loc[start_idx : total_idx - 1].copy()


def kpi_period_token(period: str) -> str:
    month = period.split()[0]
    reverse = {ru: en.title() for en, ru in MONTH_ALIASES.items()}
    return reverse.get(month, month[:3])


def kpi_fact_columns(kpi: pd.DataFrame, selected_token: str) -> list[str]:
    columns = []
    for col in kpi.columns:
        if isinstance(col, str) and col.startswith("Факт "):
            columns.append(col)
            if col == f"Факт {selected_token}":
                break
    return columns


def trend(values: list[Any]) -> str:
    nums = [v for v in values if isinstance(v, (int, float)) and not pd.isna(v)]
    if len(nums) < 2:
        return "стабильно"
    if nums[-1] < nums[-2]:
        return "просадка"
    if all(curr >= prev for prev, curr in zip(nums, nums[1:])) and nums[-1] > nums[0]:
        return "растёт"
    return "стабильно"


def md_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    align = ["---"] + ["---:" if i > 0 and headers[i] not in {"Статус", "Риски", "Событие", "Ответственный", "Привязка к показателям", "Тренд Jan→Apr", "Тренд"} else "---" for i in range(1, len(headers))]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(align) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(clean(cell)) for cell in row) + " |")
    return lines


def build_summary(input_path: Path, output_path: Path, period_arg: str | None = None) -> None:
    sheets = read_workbook(input_path)
    pl = sheets["P&L"]
    kpi = sheets["KPI команд"]
    projects = sheets["Флагманские проекты"]
    events = sheets[find_sheet(sheets, "События")]

    period = normalize_period(period_arg) if period_arg else latest_period(pl)
    previous = previous_period(pl, period)
    period_short = period.split()[0]
    selected_token = kpi_period_token(period)
    previous_label = previous or "пред. период"

    income = section_rows(pl, "ДОХОДЫ, млн руб", "Итого доходы")
    expenses = section_rows(pl, "РАСХОДЫ, млн руб", "Итого расходы")

    lines: list[str] = [f"# Exec summary за {period}", ""]
    lines += ["## 1. Финансы", "", "### Доходы, млн руб.", ""]
    income_rows = []
    for _, row in income.iterrows():
        delta = row[period] - row[previous] if previous else ""
        income_rows.append([row["Статья"], fmt(row[previous]) if previous else "", fmt(row[period]), fmt_delta(delta)])
    total_income = pl.loc[pl["Статья"] == "Итого доходы"].iloc[0]
    income_rows.append([
        "**Итого доходы**",
        f"**{fmt(total_income[previous])}**" if previous else "",
        f"**{fmt(total_income[period])}**",
        f"**{fmt_delta(total_income[period] - total_income[previous])}**" if previous else "",
    ])
    lines += md_table(["Направление", previous_label, period, f"Динамика к {previous_label}"], income_rows)

    lines += ["", "### Расходы, млн руб.", ""]
    expense_rows = []
    for _, row in expenses.iterrows():
        delta = row[period] - row[previous] if previous else ""
        expense_rows.append([row["Статья"], fmt(row[previous]) if previous else "", fmt(row[period]), fmt_delta(delta)])
    total_expenses = pl.loc[pl["Статья"] == "Итого расходы"].iloc[0]
    expense_rows.append([
        "**Итого расходы**",
        f"**{fmt(total_expenses[previous])}**" if previous else "",
        f"**{fmt(total_expenses[period])}**",
        f"**{fmt_delta(total_expenses[period] - total_expenses[previous])}**" if previous else "",
    ])
    lines += md_table(["Статья", previous_label, period, f"Динамика к {previous_label}"], expense_rows)

    lines += ["", "### EBITDA и маржа", ""]
    ebitda = pl.loc[pl["Статья"] == "EBITDA (доходы − расходы)"].iloc[0]
    margin = pl.loc[pl["Статья"] == "Маржа EBITDA, %"].iloc[0]
    ebitda_rows = [
        ["EBITDA, млн руб.", fmt(ebitda[previous]) if previous else "", fmt(ebitda[period]), fmt_delta(ebitda[period] - ebitda[previous]) if previous else ""],
        ["Маржа EBITDA, %", fmt(margin[previous]), fmt(margin[period]), fmt_delta(margin[period] - margin[previous], " п.п.") if previous else ""],
    ]
    lines += md_table(["Показатель", previous_label, period, f"Динамика к {previous_label}"], ebitda_rows)

    lines += ["", "## 2. KPI команд", ""]
    plan_col = f"План {selected_token}"
    fact_col = f"Факт {selected_token}"
    fact_cols = kpi_fact_columns(kpi, selected_token)
    kpi_rows = []
    for _, row in kpi.iterrows():
        fact_values = [row[col] for col in fact_cols]
        kpi_rows.append([
            row["Метрика"],
            fmt(row[plan_col]),
            fmt(row[fact_col]),
            " → ".join(fmt(value) for value in fact_values),
            trend(fact_values),
        ])
    lines += md_table(["Метрика", f"План {period_short}", f"Факт {period_short}", "Факт Jan→период", "Тренд"], kpi_rows)

    lines += ["", "## 3. Флагманские проекты", ""]
    project_rows = []
    for _, row in projects.iterrows():
        project_rows.append([
            row["Проект"],
            fmt(row["Бюджет план, млн"]),
            fmt(row["Факт YTD, млн"]),
            fmt(row["Выполнение, %"]),
            row["Статус"],
            row["Риски"],
        ])
    lines += md_table(["Проект", "Бюджет план, млн", "Факт YTD, млн", "Выполнение, %", "Статус", "Риски"], project_rows)

    lines += ["", f"## 4. События {period_short.lower()}", ""]
    event_rows = []
    for _, row in events.iterrows():
        event_rows.append([row["Дата"], row["Событие"], row["Ответственный"], row["Влияние на показатели"]])
    lines += md_table(["Дата", "Событие", "Ответственный", "Привязка к показателям"], event_rows)
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build monthly exec summary from monthly_report.xlsx")
    parser.add_argument("--input", default="monthly_report.xlsx", help="Input workbook path")
    parser.add_argument("--output", default="exec-summary.md", help="Output Markdown path")
    parser.add_argument("--period", default=None, help="Period label, for example: Апрель 2026")
    args = parser.parse_args()

    build_summary(Path(args.input), Path(args.output), args.period)


if __name__ == "__main__":
    main()
