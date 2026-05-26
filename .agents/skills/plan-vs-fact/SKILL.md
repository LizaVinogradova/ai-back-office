---
name: plan-vs-fact
description: Build an EBITDA plan-vs-fact workbook and markdown summary from monthly_workbook.xlsx plus any expenses_fact_1c_*.xlsx files. Use when Codex needs to aggregate flagship project revenue and expense plans, actual revenue, and 1C actual expenses by Project ID, then produce plan-vs-fact.xlsx with Excel formulas and conditional formatting plus plan-vs-fact-summary.md.
---

# Plan vs Fact

## Overview

Create a Q1-style EBITDA plan-vs-fact package by `Project ID` from:

- `monthly_workbook.xlsx`: plan revenue, plan expenses, actual revenue, contracts, team data.
- `expenses_fact_1c_*.xlsx`: any number of 1C actual-expense exports matched by glob.

The standard outputs are:

- `plan-vs-fact.xlsx`
- `plan-vs-fact-summary.md`

All sums and aggregates must be calculated by code. The workbook must contain real Excel formulas, not pasted final numbers.

## Workflow

1. Confirm the project root contains `monthly_workbook.xlsx` and one or more `expenses_fact_1c_*.xlsx` files.
2. Run the bundled script from the project root:

```powershell
python .agents\skills\plan-vs-fact\scripts\build_plan_vs_fact.py
```

3. Verify the generated workbook:
   - sheet `Сводка` exists;
   - sheet `Детализация` exists;
   - hidden helper sheet `Данные_доходы` exists;
   - `Сводка` has 5 project rows plus `Итого`;
   - summary formulas include `SUMIFS`, EBITDA formulas, and `IFERROR` for percentage deviation;
   - EBITDA deviation columns have conditional formatting: green for fact >= plan, red for worse.
4. Verify `plan-vs-fact-summary.md` contains the same summary table and an итоговая строка.

## Workbook Contract

### `Сводка`

Columns:

- `Project ID`
- `Проект`
- `План доходов, тыс ₽`
- `Факт доходов, тыс ₽`
- `План расходов, тыс ₽`
- `Факт расходов, тыс ₽`
- `EBITDA-план, тыс ₽`
- `EBITDA-факт, тыс ₽`
- `Отклонение EBITDA, тыс ₽`
- `Отклонение EBITDA, %`

Use Excel formulas for all calculated numeric columns:

- plan/fact totals: `SUMIFS`
- EBITDA plan: plan revenue minus plan expenses
- EBITDA fact: actual revenue minus actual expenses
- deviation: EBITDA fact minus EBITDA plan
- deviation percent: `IFERROR(deviation / ABS(EBITDA plan), 0)`

### `Детализация`

Rows must be expense detail by:

- `Project ID`
- project name
- month
- expense article
- planned expense
- actual 1C expense

Keep all planned rows and include any extra actual 1C rows even if the article was not present in the plan.

### `plan-vs-fact-summary.md`

Save a markdown table with the same project-level summary as `Сводка`, including `Итого`. This file is used for automated checks.

## Source Mapping

- `monthly_workbook.xlsx / План - доходы`: plan revenue by `Project ID`, source, month columns.
- `monthly_workbook.xlsx / Факт - доходы`: actual revenue by `Project ID`, `Дата`, `Сумма, ₽`.
- `monthly_workbook.xlsx / План - расходы`: planned expenses by `Project ID`, article, month columns.
- `expenses_fact_1c_*.xlsx`: actual expenses by `Код проекта`, `Статья (1С)`, `Дата`, `Сумма, ₽`.

Normalize 1C exports:

- Treat `Код проекта` as `Project ID`.
- Convert `Сумма, ₽` to thousand rubles.
- Derive month as `YYYY-MM` from `Дата`.
- Strip the account prefix from `Статья (1С)` after `—` when present.

## Validation Command

Use this compact check after generation:

```powershell
python -c "from openpyxl import load_workbook; wb=load_workbook('plan-vs-fact.xlsx', data_only=False); ws=wb['Сводка']; print(wb.sheetnames); print(ws['C2'].value, ws['G2'].value, ws['J2'].value); print(len(ws.conditional_formatting))"
```
