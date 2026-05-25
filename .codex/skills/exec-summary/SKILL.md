---
name: exec-summary
description: Build a factual monthly executive summary from the project workbook monthly_report.xlsx. Use when the user asks to create or refresh exec-summary.md from the four-sheet monthly report with P&L, KPI команд, Флагманские проекты, and События data; supports a specified period or defaults to the latest month with data.
---

# Exec Summary

## Overview

Generate `exec-summary.md` in the project root from `monthly_report.xlsx`. The output must be structured fact only: no conclusions, recommendations, or evaluative commentary.

## Workflow

1. Locate `monthly_report.xlsx` in the project root unless the user provides another path.
2. Read all four report sheets:
   - `P&L`
   - `KPI команд`
   - `Флагманские проекты`
   - the sheet whose name starts with `События`
3. Determine the reporting period:
   - Use the user's requested period when provided.
   - Otherwise use the latest month column with data in `P&L`, excluding `YTD итог`.
4. Build four sections:
   - `Финансы`: April-style selected-period income by direction, expenses by category, totals, EBITDA, EBITDA margin, and period-over-period dynamics versus the previous month when available.
   - `KPI команд`: all metrics with selected-period plan/fact plus fact trend across months up to the selected period.
   - `Флагманские проекты`: all projects with completion percent, status, and risk.
   - `События`: all events from the events sheet with date, event, owner, and link to indicators.
5. Save the result as `exec-summary.md` in the project root.
6. Verify counts against the workbook: all income directions, expense categories, KPI metrics, flagship projects, and event rows should be represented.

## Recommended Command

Run the bundled script from the project root:

```powershell
python .codex\skills\exec-summary\scripts\build_exec_summary.py
```

For a specific period:

```powershell
python .codex\skills\exec-summary\scripts\build_exec_summary.py --period "Апрель 2026"
```

The script accepts:

- `--input`: workbook path, default `monthly_report.xlsx`
- `--output`: Markdown output path, default `exec-summary.md`
- `--period`: selected month label; if omitted, use the latest month with data

## Output Rules

- Preserve workbook facts and wording.
- Do not add interpretations, recommendations, or performance assessments beyond source statuses/risks already present in the workbook.
- Use Markdown tables for factual sections.
- Show dynamics as numeric deltas versus the previous month when a previous month exists.
- For KPI trend labels, use only `растёт`, `стабильно`, or `просадка`.
