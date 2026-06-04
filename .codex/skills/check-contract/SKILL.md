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

1. Run the bundled script from the project root, using the path where this skill is installed:

```powershell
python .agents\skills\check-contract\scripts\check_contract.py contract-B.md
```

If using the `.codex` copy:

```powershell
python .codex\skills\check-contract\scripts\check_contract.py contract-B.md
```

2. If the user provides another contract path, pass that path instead:

```powershell
python .agents\skills\check-contract\scripts\check_contract.py path\to\contract.md
```

3. Verify the output:
   - exactly one block per violation;
   - each block includes a direct quote from the contract with the contract point;
   - each block links to a concrete legal-base file and point with a direct quote;
   - include only violations against the legal base, not general legal drafting suggestions.

## Expected Checks

Check mandatory regulatory mismatches from:

- `policy-vendor-contracts.md`: payment term, advance percentage, contractor delay penalty, warranty period, currency, unilateral termination trigger;
- `corporate-standard-vendors-part3.md`: required contract structure, jurisdiction, IP rights transfer, confidentiality/NDA;
- `security-checklist.md`: red flags stated directly in contract text, especially missing confidentiality/NDA;
- `auditor-letter.md`: use as support for IP-rights and personal-data issues when applicable;
- `tax-consultant-clarification.md`: use only when the contract text itself creates a direct primary-document mismatch required by the task.

For the known `contract-B.md` exercise, the expected report contains five violations: advance, payment term, penalty, IP rights transfer, and confidentiality/NDA.
