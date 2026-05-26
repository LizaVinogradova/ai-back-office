from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


PROJECT_ID = "PRJ-2026-003"
PROJECT_NAME = "Цифровая платформа 2.0"
WORKBOOK = Path("monthly_workbook.xlsx")
OUTPUT = Path("one-pager.md")


def money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def money_1(value: float) -> str:
    return f"{value:,.1f}".replace(",", " ")


def pct(value: float) -> str:
    return f"{value:.1f}%"


def plan_columns(df: pd.DataFrame) -> list[str]:
    return [col for col in df.columns if isinstance(col, str) and col.startswith("План ")]


def month_from_plan_col(col: str) -> str:
    match = re.search(r"(\d{4}-\d{2})", col)
    if not match:
        raise ValueError(f"Cannot extract month from column {col!r}")
    return match.group(1)


def read_sheet(name: str) -> pd.DataFrame:
    return pd.read_excel(WORKBOOK, sheet_name=name)


def make_month_table(rows: list[dict[str, object]], value_columns: list[str]) -> list[str]:
    headers = ["Показатель", *value_columns, "Итого"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| --- | " + " | ".join("---:" for _ in value_columns) + " | ---: |",
    ]
    for row in rows:
        values = [str(row["Показатель"])]
        values.extend(str(row[col]) for col in value_columns)
        values.append(str(row["Итого"]))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def main() -> None:
    team = read_sheet("Команда")
    plan_expenses = read_sheet("План - расходы")
    plan_income = read_sheet("План - доходы")
    actual_income = read_sheet("Факт - доходы")
    contracts = read_sheet("Контракты")

    team = team[team["Project ID"] == PROJECT_ID].copy()
    plan_expenses = plan_expenses[plan_expenses["Project ID"] == PROJECT_ID].copy()
    plan_income = plan_income[plan_income["Project ID"] == PROJECT_ID].copy()
    actual_income = actual_income[actual_income["Project ID"] == PROJECT_ID].copy()
    contracts = contracts[contracts["Project ID"] == PROJECT_ID].copy()

    expense_cols = plan_columns(plan_expenses)
    income_cols = plan_columns(plan_income)
    months = [month_from_plan_col(col) for col in income_cols]

    plan_income_by_month = {
        month_from_plan_col(col): float(plan_income[col].sum()) for col in income_cols
    }
    plan_expenses_by_month = {
        month_from_plan_col(col): float(plan_expenses[col].sum()) for col in expense_cols
    }

    actual_income["Дата"] = pd.to_datetime(actual_income["Дата"], dayfirst=True)
    actual_income["Месяц"] = actual_income["Дата"].dt.strftime("%Y-%m")
    actual_income_by_month = {
        month: float(actual_income.loc[actual_income["Месяц"] == month, "Сумма, ₽"].sum()) / 1000
        for month in months
    }

    ebitda_plan_by_month = {
        month: plan_income_by_month.get(month, 0) - plan_expenses_by_month.get(month, 0)
        for month in months
    }

    team["Плановая загрузка, тыс ₽/мес"] = (
        team["Ставка, тыс ₽/мес"] * team["% занятости"] / 100
    )
    team_people = (
        team.groupby(["Сотрудник", "Роль"], as_index=False)
        .agg(
            Месяцы=("Месяц", lambda values: ", ".join(sorted(map(str, values.unique())))),
            Средняя_занятость=("% занятости", "mean"),
            Ставка=("Ставка, тыс ₽/мес", "first"),
            Плановая_нагрузка=("Плановая загрузка, тыс ₽/мес", "sum"),
        )
        .sort_values(["Роль", "Сотрудник"])
    )
    team_cost_by_month = (
        team.groupby("Месяц")["Плановая загрузка, тыс ₽/мес"].sum().to_dict()
    )

    income_source_rows = []
    for _, row in plan_income.iterrows():
        values = [float(row[col]) for col in income_cols]
        income_source_rows.append([row["Источник"], *[money(v) for v in values], money(sum(values))])

    expense_rows = []
    for _, row in plan_expenses.iterrows():
        values = [float(row[col]) for col in expense_cols]
        expense_rows.append([row["Статья"], *[money(v) for v in values], money(sum(values))])

    actual_by_source = (
        actual_income.groupby("Источник")["Сумма, ₽"].sum().div(1000).reset_index()
    )

    total_plan_income = sum(plan_income_by_month.values())
    total_actual_income = sum(actual_income_by_month.values())
    total_plan_expenses = sum(plan_expenses_by_month.values())
    total_ebitda_plan = sum(ebitda_plan_by_month.values())
    total_contracts = float(contracts["Сумма по договору, тыс ₽"].sum())
    fact_vs_plan = total_actual_income - total_plan_income
    fact_plan_pct = total_actual_income / total_plan_income * 100 if total_plan_income else 0

    lines: list[str] = [
        f"# One-pager: {PROJECT_NAME}",
        "",
        f"- Project ID: `{PROJECT_ID}`",
        f"- Период данных: {months[0]} — {months[-1]}",
        f"- План доходов: **{money(total_plan_income)} тыс ₽**",
        f"- Факт доходов: **{money(total_actual_income)} тыс ₽** ({pct(fact_plan_pct)} от плана; отклонение {money_1(fact_vs_plan)} тыс ₽)",
        f"- План расходов: **{money(total_plan_expenses)} тыс ₽**",
        f"- EBITDA-план: **{money(total_ebitda_plan)} тыс ₽**",
        f"- Контракты: **{money(total_contracts)} тыс ₽**",
        "",
        "## Команда",
        "",
        f"- Участников: **{team_people['Сотрудник'].nunique()}**",
        f"- Плановая нагрузка ФОТ по данным листа `Команда`: **{money(sum(team_cost_by_month.values()))} тыс ₽** за период",
        "",
        "| Сотрудник | Роль | Месяцы | Ставка, тыс ₽/мес | Средняя занятость | Плановая нагрузка, тыс ₽ |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]

    for _, row in team_people.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["Сотрудник"]),
                    str(row["Роль"]),
                    str(row["Месяцы"]),
                    money(float(row["Ставка"])),
                    pct(float(row["Средняя_занятость"])),
                    money_1(float(row["Плановая_нагрузка"])),
                ]
            )
            + " |"
        )

    lines += [
        "",
        "## План / факт доходов",
        "",
    ]

    income_rows = [
        {
            "Показатель": "План доходов, тыс ₽",
            **{month: money(plan_income_by_month[month]) for month in months},
            "Итого": money(total_plan_income),
        },
        {
            "Показатель": "Факт доходов, тыс ₽",
            **{month: money(actual_income_by_month[month]) for month in months},
            "Итого": money(total_actual_income),
        },
        {
            "Показатель": "Отклонение факт-план, тыс ₽",
            **{month: money_1(actual_income_by_month[month] - plan_income_by_month[month]) for month in months},
            "Итого": money_1(fact_vs_plan),
        },
        {
            "Показатель": "Факт / план",
            **{month: pct(actual_income_by_month[month] / plan_income_by_month[month] * 100) for month in months},
            "Итого": pct(fact_plan_pct),
        },
    ]
    lines += make_month_table(income_rows, months)

    lines += [
        "",
        "### План доходов по источникам, тыс ₽",
        "",
        "| Источник | " + " | ".join(months) + " | Итого |",
        "| --- | " + " | ".join("---:" for _ in months) + " | ---: |",
    ]
    for row in income_source_rows:
        lines.append("| " + " | ".join(map(str, row)) + " |")

    lines += [
        "",
        "### Факт доходов по источникам",
        "",
        "| Источник | Факт, тыс ₽ |",
        "| --- | ---: |",
    ]
    for _, row in actual_by_source.iterrows():
        lines.append(f"| {row['Источник']} | {money_1(float(row['Сумма, ₽']))} |")

    lines += [
        "",
        "## План расходов",
        "",
    ]
    expense_summary_rows = [
        {
            "Показатель": "План расходов, тыс ₽",
            **{month: money(plan_expenses_by_month[month]) for month in months},
            "Итого": money(total_plan_expenses),
        }
    ]
    lines += make_month_table(expense_summary_rows, months)
    lines += [
        "",
        "| Статья | " + " | ".join(months) + " | Итого |",
        "| --- | " + " | ".join("---:" for _ in months) + " | ---: |",
    ]
    for row in expense_rows:
        lines.append("| " + " | ".join(map(str, row)) + " |")

    lines += [
        "",
        "## Контракты",
        "",
        "| Контрагент | Тип услуг | Сумма, тыс ₽ | Дата заключения |",
        "| --- | --- | ---: | --- |",
    ]
    for _, row in contracts.sort_values("Дата заключения").iterrows():
        lines.append(
            f"| {row['Контрагент']} | {row['Тип услуг']} | {money(float(row['Сумма по договору, тыс ₽']))} | {row['Дата заключения']} |"
        )

    lines += [
        "",
        "## EBITDA-план",
        "",
    ]
    ebitda_rows = [
        {
            "Показатель": "План доходов, тыс ₽",
            **{month: money(plan_income_by_month[month]) for month in months},
            "Итого": money(total_plan_income),
        },
        {
            "Показатель": "План расходов, тыс ₽",
            **{month: money(plan_expenses_by_month[month]) for month in months},
            "Итого": money(total_plan_expenses),
        },
        {
            "Показатель": "EBITDA-план, тыс ₽",
            **{month: money(ebitda_plan_by_month[month]) for month in months},
            "Итого": money(total_ebitda_plan),
        },
    ]
    lines += make_month_table(ebitda_rows, months)
    lines.append("")

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
