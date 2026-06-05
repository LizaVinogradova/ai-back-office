---
name: check-contract
description: Check a contractor agreement against the local regulations/ legal base and generate compliance-report.md. Use when the user invokes $check-contract <contract.md> or asks to verify a contract against contract compliance rules, corporate vendor policy, security checklist, auditor notes, and tax-consultant clarification files.
---

# Check Contract

## Overview

Generate `compliance-report.md` for a Markdown contract by comparing it with the legal base in `regulations/`.

The standard input is:

- a contract Markdown file, passed by the user, for example `contract-B.md`;
- all five files from `regulations/`.

The standard output is:

- `compliance-report.md` in the project root.

## Workflow

1. Generator: read the contract and all five `regulations/` files. Produce a draft report with direct quotes and links to legal-base points. Keep quotes literal: copy exact source substrings without normalization, ellipses, glued fragments, or paraphrase.

2. Validator-subagent: launch a strict quote validator after the draft report is written. Pass it the report, the contract, and all legal-base files. Use this instruction verbatim:

```text
Ты — строгий валидатор цитат. На вход — отчёт первого агента, договор и правовая база. Для каждой цитаты найди её буквально в указанном источнике (точное совпадение текста). Верни «ОК» если найдена буквально, «такой цитаты нет» если есть любое расхождение — перефразировка, склейка, недосказанность. Не интерпретируй смысл. Только буквальное совпадение.
```

Record the validator result in the run notes: which quotes are `ОК`, which are `такой цитаты нет`, and the overall status.

3. Claim: if any quote is marked `такой цитаты нет`, return a claim to the generator:

```text
Эти цитаты не найдены в источнике буквально: [список]. Переделай отчёт: убери, замени или уточни эти замечания.
```

4. Loop: repeat generator, validator, and claim up to 3 iterations. If the report still has quote mismatches after 3 iterations, keep the final report with the status `не сошлось, требует ручной проверки`. If all quotes pass, mark the report `ОК` and record the iteration count.

## Scripted Run

Run the bundled script from the project root, using the path where this skill is installed. The script implements the generator plus an internal exact-substring validator loop so batch output is reproducible. For a training/demo run, still launch the external Validator-subagent once and compare its response with the internal status:

```powershell
python .agents\skills\check-contract\scripts\check_contract.py contract-B.md
```

If using the `.codex` copy:

```powershell
python .codex\skills\check-contract\scripts\check_contract.py contract-B.md
```

If the user provides another contract path, pass that path instead:

```powershell
python .agents\skills\check-contract\scripts\check_contract.py path\to\contract.md
```

Verify the output:
   - exactly one block per violation;
   - each block includes a direct quote from the contract with the contract point;
   - each block links to a concrete legal-base file and point with a direct quote;
   - `Статус валидации цитат` is `ОК`, or the report is explicitly marked as requiring manual review after 3 iterations;
   - include only violations against the legal base, not general legal drafting suggestions.

## Expected Checks

Check mandatory regulatory mismatches from:

- `policy-vendor-contracts.md`: payment term, advance percentage, contractor delay penalty, warranty period, currency, unilateral termination trigger;
- `corporate-standard-vendors-part3.md`: required contract structure, jurisdiction, IP rights transfer, confidentiality/NDA;
- `security-checklist.md`: red flags stated directly in contract text, especially missing confidentiality/NDA;
- `auditor-letter.md`: use as support for IP-rights and personal-data issues when applicable;
- `tax-consultant-clarification.md`: use only when the contract text itself creates a direct primary-document mismatch required by the task.

For the known `contract-B.md` exercise, the expected report contains five violations: advance, payment term, penalty, IP rights transfer, and confidentiality/NDA.
