from __future__ import annotations

import argparse
import re
from pathlib import Path


REG_FILES = [
    "auditor-letter.md",
    "corporate-standard-vendors-part3.md",
    "policy-vendor-contracts.md",
    "security-checklist.md",
    "tax-consultant-clarification.md",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def point(text: str, number: str) -> str:
    pattern = rf"(?ms)^(?:\*\*)?{re.escape(number)}\.(?:\*\*)?\s*.*?(?=^\s*(?:\*\*)?\d+(?:\.\d+)?\.|\Z)"
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Cannot find point {number}")
    return match.group(0).strip()


def contract_point(text: str, number: str) -> str:
    pattern = rf"(?ms)^{re.escape(number)}\.\s*.*?(?=^\d+\.\d+\.|^## |\Z)"
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Cannot find contract point {number}")
    return match.group(0).strip()


def contract_points(text: str) -> list[tuple[str, str]]:
    return [
        (match.group(1), match.group(0).strip())
        for match in re.finditer(r"(?ms)^(\d+\.\d+)\.\s*.*?(?=^\d+\.\d+\.|^## |\Z)", text)
    ]


def find_contract_point(text: str, *patterns: str) -> tuple[str, str] | None:
    for number, item in contract_points(text):
        lowered = item.lower()
        if all(pattern.lower() in lowered for pattern in patterns):
            return number, item
    return None


def percent_value(text: str) -> float | None:
    match = re.search(r"(\d+(?:[,.]\d+)?)\s*%", text)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def first_number_before_working_days(text: str) -> int | None:
    match = re.search(r"(\d+)\s*(?:\([^)]*\)\s*)?рабоч", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)\s*(?:\([^)]*\)\s*)?месяц", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def literal_line(text: str, startswith: str) -> str:
    for line in text.splitlines():
        if line.startswith(startswith):
            return line
    raise ValueError(f"Cannot find line starting with {startswith!r}")


def section_heading(text: str, heading: str) -> str:
    for line in text.splitlines():
        if line == heading:
            return line
    raise ValueError(f"Cannot find heading {heading!r}")


def quote(text: str) -> str:
    return f"> «{text}»"


def has_confidentiality(text: str) -> bool:
    return bool(re.search(r"(?i)конфиденциальност|NDA|неразглаш", text))


def validate_findings(findings: list[dict[str, object]], sources: dict[str, str]) -> list[str]:
    missing: list[str] = []
    for idx, finding in enumerate(findings, start=1):
        for item in finding["contract_quotes"]:
            quote_text = str(item)
            if quote_text not in sources["contract"]:
                missing.append(f"Нарушение {idx}: цитата из договора не найдена буквально: {quote_text}")
        for file_name, ref_point, ref_text in finding["legal_refs"]:
            quote_text = str(ref_text)
            source_key = str(file_name).replace("regulations/", "")
            if quote_text not in sources[source_key]:
                missing.append(
                    f"Нарушение {idx}: цитата из правовой базы {file_name}, пункт {ref_point} не найдена буквально: {quote_text}"
                )
    return missing


def build_findings(contract: str, regs: dict[str, str]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []

    advance = find_contract_point(contract, "авансов")
    if advance and (percent_value(advance[1]) or 0) > 30:
        findings.append(
            {
                "title": "Аванс превышает допустимый лимит",
                "contract_point": advance[0],
                "contract_quotes": [advance[1]],
                "legal_refs": [
                    (
                        "regulations/policy-vendor-contracts.md",
                        "2.2",
                        point(regs["policy-vendor-contracts.md"], "2.2"),
                    )
                ],
                "conclusion": "Договор устанавливает аванс выше 30%, тогда как базовый лимит правовой базы составляет 30%.",
            }
        )

    payment = find_contract_point(contract, "окончательный", "расч")
    payment_days = first_number_before_working_days(payment[1]) if payment else None
    if payment and payment_days and payment_days > 30:
        findings.append(
            {
                "title": "Срок окончательного расчёта превышает допустимый срок оплаты",
                "contract_point": payment[0],
                "contract_quotes": [payment[1]],
                "legal_refs": [
                    (
                        "regulations/policy-vendor-contracts.md",
                        "2.1",
                        point(regs["policy-vendor-contracts.md"], "2.1"),
                    )
                ],
                "conclusion": "Договор предусматривает срок оплаты больше 30 рабочих дней, что превышает предельный срок правовой базы.",
            }
        )

    penalty = find_contract_point(contract, "наруш", "срок", "неустойк")
    penalty_value = percent_value(penalty[1]) if penalty else None
    if penalty and penalty_value is not None and penalty_value < 0.5:
        findings.append(
            {
                "title": "Неустойка за просрочку подрядчика ниже обязательного минимума",
                "contract_point": penalty[0],
                "contract_quotes": [penalty[1]],
                "legal_refs": [
                    (
                        "regulations/policy-vendor-contracts.md",
                        "2.3",
                        point(regs["policy-vendor-contracts.md"], "2.3"),
                    )
                ],
                "conclusion": "Договор устанавливает неустойку за день просрочки ниже обязательного минимума 0,5%.",
            }
        )

    warranty = find_contract_point(contract, "гарант", "качество") or find_contract_point(contract, "гарантию")
    warranty_months = first_number_before_working_days(warranty[1]) if warranty else None
    if warranty and warranty_months and warranty_months < 12:
        findings.append(
            {
                "title": "Гарантийный срок меньше обязательного минимума",
                "contract_point": warranty[0],
                "contract_quotes": [warranty[1]],
                "legal_refs": [
                    (
                        "regulations/policy-vendor-contracts.md",
                        "2.4",
                        point(regs["policy-vendor-contracts.md"], "2.4"),
                    )
                ],
                "conclusion": "Договор устанавливает гарантийный срок меньше 12 месяцев, что нарушает обязательный минимум правовой базы.",
            }
        )

    ip_start = find_contract_point(contract, "исключительные права")
    ip_quotes = []
    if ip_start:
        all_points = contract_points(contract)
        start_idx = next((idx for idx, (num, _) in enumerate(all_points) if num == ip_start[0]), None)
        if start_idx is not None:
            ip_quotes = [text for _, text in all_points[start_idx : start_idx + 3]]
    if ip_quotes and ("остаются у Подрядчика" in ip_quotes[0] or "неисключительная лицензия" in ip_quotes[0]):
        findings.append(
            {
                "title": "Исключительные права на результат работ не переходят к Заказчику",
                "contract_point": f"{ip_start[0]} и связанные пункты",
                "contract_quotes": ip_quotes,
                "legal_refs": [
                    (
                        "regulations/corporate-standard-vendors-part3.md",
                        "2.3",
                        point(regs["corporate-standard-vendors-part3.md"], "2.3"),
                    ),
                    (
                        "regulations/auditor-letter.md",
                        "1",
                        point(regs["auditor-letter.md"], "1"),
                    ),
                ],
                "conclusion": "Договор сохраняет исключительные права за Подрядчиком и предоставляет только неисключительную лицензию, что запрещено корпоративным стандартом для договоров на создание ПО.",
            }
        )

    if not has_confidentiality(contract):
        findings.append(
            {
                "title": "В договоре отсутствует обязательный раздел о конфиденциальности",
                "contract_point": "структура разделов 7-8 и пункт 12.5",
                "contract_quotes": [
                    section_heading(contract, "## 7. Переход прав на результаты интеллектуальной деятельности"),
                    section_heading(contract, "## 8. Гарантии и ответственность"),
                    contract_point(contract, "12.5"),
                ],
                "legal_refs": [
                    (
                        "regulations/corporate-standard-vendors-part3.md",
                        "2.5",
                        point(regs["corporate-standard-vendors-part3.md"], "2.5"),
                    ),
                    (
                        "regulations/security-checklist.md",
                        "red flag 3",
                        literal_line(regs["security-checklist.md"], "3. **Red flag:**"),
                    ),
                ],
                "conclusion": "В договоре нет раздела «Конфиденциальность» и нет приложения NDA; это нарушает корпоративный стандарт и является red flag службы безопасности.",
            }
        )

    return findings


def render_report(
    contract_path: Path,
    findings: list[dict[str, object]],
    output_path: Path,
    validation_attempts: int,
    missing_quotes: list[str],
) -> None:
    lines: list[str] = [
        f"# Compliance report: {contract_path.name} vs правовая база",
        "",
        "## Область проверки",
        "",
        f"Проверен договор `{contract_path.as_posix()}` относительно правовой базы из папки `regulations/`:",
        "",
    ]
    lines.extend(f"- `regulations/{name}`" for name in REG_FILES)
    lines.extend(
        [
            "",
            "В отчёт включены только нарушения требований или прямых контрольных правил правовой базы. Общие юридические замечания, не подтверждённые конкретным пунктом правовой базы, не включались.",
            "",
        ]
    )

    validation_status = "ОК" if not missing_quotes else "не сошлось, требует ручной проверки"
    lines.extend(
        [
            f"**Статус валидации цитат:** {validation_status}.",
            f"**Итераций валидации:** {validation_attempts}.",
            "",
        ]
    )

    if missing_quotes:
        lines.extend(["**Цитаты, не найденные буквально:**", ""])
        lines.extend(f"- {item}" for item in missing_quotes)
        lines.append("")

    for idx, finding in enumerate(findings, start=1):
        lines.extend(
            [
                f"## Нарушение {idx}. {finding['title']}",
                "",
                f"**Пункт договора:** {finding['contract_point']}.",
                "",
                "**Цитата из договора:**" if len(finding["contract_quotes"]) == 1 else "**Цитаты из договора:**",
                "",
            ]
        )
        for item in finding["contract_quotes"]:
            lines.extend([quote(str(item)), ""])
        for ref_idx, (file_name, ref_point, ref_text) in enumerate(finding["legal_refs"]):
            label = "**Пункт правовой базы:**" if ref_idx == 0 else "**Дополнительный пункт правовой базы:**"
            quote_label = "**Цитата из правовой базы:**" if ref_idx == 0 else "**Цитата из дополнительного источника:**"
            lines.extend(
                [
                    f"{label} [`{file_name}`, пункт {ref_point}]({file_name}).",
                    "",
                    quote_label,
                    "",
                    quote(str(ref_text)),
                    "",
                ]
            )
        lines.extend([f"**Вывод:** {finding['conclusion']}", ""])

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_report(contract_path: Path, regulations_dir: Path, output_path: Path) -> None:
    contract = read(contract_path)
    regs = {name: read(regulations_dir / name) for name in REG_FILES}

    missing = [name for name in REG_FILES if not (regulations_dir / name).exists()]
    if missing:
        raise FileNotFoundError("Missing regulations files: " + ", ".join(missing))

    sources = {"contract": contract, **regs}
    missing_quotes: list[str] = []
    findings: list[dict[str, object]] = []
    attempts = 0

    for attempts in range(1, 4):
        findings = build_findings(contract, regs)
        missing_quotes = validate_findings(findings, sources)
        if not missing_quotes:
            break

    render_report(contract_path, findings, output_path, attempts, missing_quotes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check contract against local regulations and write compliance-report.md")
    parser.add_argument("contract", type=Path)
    parser.add_argument("--regulations", type=Path, default=Path("regulations"))
    parser.add_argument("--output", type=Path, default=Path("compliance-report.md"))
    args = parser.parse_args()
    build_report(args.contract, args.regulations, args.output)


if __name__ == "__main__":
    main()
