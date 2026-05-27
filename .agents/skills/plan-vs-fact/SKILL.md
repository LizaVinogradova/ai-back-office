---
name: plan-vs-fact
description: Build an EBITDA plan-vs-fact workbook and markdown summary from monthly_workbook.xlsx, any expenses_fact_1c_*.xlsx files, and optional PDF acts from acts-incoming/. Use when Codex needs to aggregate flagship project revenue and expense plans, actual revenue, 1C actual expenses, categorize incoming PDF acts by Project ID/article through a human-in-the-loop confirmation CSV, then produce plan-vs-fact.xlsx with Excel formulas and conditional formatting plus plan-vs-fact-summary.md.
---

# Plan vs Fact

## Overview

Create a Q1-style EBITDA plan-vs-fact package by `Project ID` from:

- `monthly_workbook.xlsx`: plan revenue, plan expenses, actual revenue, contracts, team data.
- `expenses_fact_1c_*.xlsx`: any number of 1C actual-expense exports matched by glob.
- `acts-incoming/*.pdf` when present: incoming service acts that need human confirmation before inclusion.

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

3. If `acts-incoming/` exists, the script first creates or reads `acts-categorized.csv`:
   - columns must be `дата`, `№ акта`, `контрагент`, `сумма`, `project_id`, `статья`, `подтверждено`;
   - on first run, the script proposes categorization and stops before writing workbook outputs;
   - show the proposed rows to the user and ask for confirmation;
   - write `yes`/`да`/`true`/`1` in `подтверждено` to include an act;
   - write `no`/`нет`/`false`/`0` in `подтверждено` to reject an act;
   - rerun the script only after every act is confirmed or rejected.
4. Verify the generated workbook:
   - sheet `Сводка` exists;
   - sheet `Детализация` exists;
   - hidden helper sheet `Данные_доходы` exists;
   - `Сводка` has 5 project rows plus `Итого`;
   - summary formulas include `SUMIFS`, EBITDA formulas, and `IFERROR` for percentage deviation;
   - EBITDA deviation columns have conditional formatting: green for fact >= plan, red for worse.
5. Verify `plan-vs-fact-summary.md` contains the same summary table and an итоговая строка.

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

Confirmed PDF acts are appended as actual expense rows:

- month comes from the act date;
- plan expense is `0` unless a matching plan row exists;
- fact expense is the confirmed act amount converted to thousand rubles;
- only rows confirmed in `acts-categorized.csv` are included.

### `plan-vs-fact-summary.md`

Save a markdown table with the same project-level summary as `Сводка`, including `Итого`. This file is used for automated checks.

## Source Mapping

- `monthly_workbook.xlsx / План - доходы`: plan revenue by `Project ID`, source, month columns.
- `monthly_workbook.xlsx / Факт - доходы`: actual revenue by `Project ID`, `Дата`, `Сумма, ₽`.
- `monthly_workbook.xlsx / План - расходы`: planned expenses by `Project ID`, article, month columns.
- `expenses_fact_1c_*.xlsx`: actual expenses by `Код проекта`, `Статья (1С)`, `Дата`, `Сумма, ₽`.
- `acts-incoming/*.pdf`: optional incoming acts parsed for date, act number, contractor, amount, project, and proposed article.

Normalize 1C exports:

- Treat `Код проекта` as `Project ID`.
- Convert `Сумма, ₽` to thousand rubles.
- Derive month as `YYYY-MM` from `Дата`.
- Strip the account prefix from `Статья (1С)` after `—` when present.

Normalize acts:

- Extract date from the act header.
- Extract act number from `АКТ № ...`.
- Extract contractor from the first executor line.
- Extract amount from `Всего к оплате`.
- Map `Проект Заказчика` to `Project ID`.
- Propose article by keywords, then require user confirmation in `acts-categorized.csv`.

## Validation Command

Use this compact check after generation:

```powershell
python -c "from openpyxl import load_workbook; wb=load_workbook('plan-vs-fact.xlsx', data_only=False); ws=wb['Сводка']; print(wb.sheetnames); print(ws['C2'].value, ws['G2'].value, ws['J2'].value); print(len(ws.conditional_formatting))"
```
