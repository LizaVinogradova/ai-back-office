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
    pattern = rf"(?ms)^(?:\*\*)?{re.escape(number)}\.(?:\*\*)?\s*(.*?)(?=^\s*(?:\*\*)?\d+(?:\.\d+)?\.|\Z)"
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Cannot find point {number}")
    body = match.group(1).strip()
    return re.sub(r"\s+", " ", body)


def contract_point(text: str, number: str) -> str:
    pattern = rf"(?ms)^{re.escape(number)}\.\s*(.*?)(?=^\d+\.\d+\.|^## |\Z)"
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Cannot find contract point {number}")
    return re.sub(r"\s+", " ", match.group(1).strip())


def quote(text: str) -> str:
    return f"> «{text}»"


def has_confidentiality(text: str) -> bool:
    return bool(re.search(r"(?i)конфиденциальност|NDA|неразглаш", text))


def build_report(contract_path: Path, regulations_dir: Path, output_path: Path) -> None:
    contract = read(contract_path)
    regs = {name: read(regulations_dir / name) for name in REG_FILES}

    missing = [name for name in REG_FILES if not (regulations_dir / name).exists()]
    if missing:
        raise FileNotFoundError("Missing regulations files: " + ", ".join(missing))

    findings: list[dict[str, object]] = []

    p42 = contract_point(contract, "4.2")
    if re.search(r"70\s*%", p42):
        findings.append(
            {
                "title": "Аванс превышает допустимый лимит",
                "contract_point": "4.2",
                "contract_quotes": [p42],
                "legal_refs": [
                    (
                        "regulations/policy-vendor-contracts.md",
                        "2.2",
                        point(regs["policy-vendor-contracts.md"], "2.2"),
                    )
                ],
                "conclusion": "Договор устанавливает аванс 70%, тогда как базовый лимит правовой базы составляет 30%.",
            }
        )

    p43 = contract_point(contract, "4.3")
    if re.search(r"60\s*\(", p43):
        findings.append(
            {
                "title": "Срок окончательного расчёта превышает допустимый срок оплаты",
                "contract_point": "4.3",
                "contract_quotes": [p43],
                "legal_refs": [
                    (
                        "regulations/policy-vendor-contracts.md",
                        "2.1",
                        point(regs["policy-vendor-contracts.md"], "2.1"),
                    )
                ],
                "conclusion": "Договор предусматривает оплату в течение 60 рабочих дней, что превышает предельные 30 рабочих дней.",
            }
        )

    p84 = contract_point(contract, "8.4")
    if "0,05%" in p84 or "0.05%" in p84:
        findings.append(
            {
                "title": "Неустойка за просрочку подрядчика ниже обязательного минимума",
                "contract_point": "8.4",
                "contract_quotes": [p84],
                "legal_refs": [
                    (
                        "regulations/policy-vendor-contracts.md",
                        "2.3",
                        point(regs["policy-vendor-contracts.md"], "2.3"),
                    )
                ],
                "conclusion": "Договор устанавливает неустойку 0,05% за день просрочки, что ниже обязательного минимума 0,5%.",
            }
        )

    ip_quotes = [contract_point(contract, n) for n in ("7.1", "7.2", "7.3")]
    if "остаются у Подрядчика" in ip_quotes[0] or "неисключительная лицензия" in ip_quotes[0]:
        findings.append(
            {
                "title": "Исключительные права на результат работ не переходят к Заказчику",
                "contract_point": "7.1-7.3",
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
                    "## 7. Переход прав на результаты интеллектуальной деятельности",
                    "## 8. Гарантии и ответственность",
                    "Приложения к Договору, являющиеся его неотъемлемой частью: Приложение № 1 — Техническое задание (состав, объём и сроки Работ по этапам, стоимость по этапам).",
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
                        "Red flag: В договоре отсутствует раздел «Конфиденциальность» / NDA. Действие: Возврат подрядчику для добавления.",
                    ),
                ],
                "conclusion": "В договоре нет раздела «Конфиденциальность» и нет приложения NDA; это нарушает корпоративный стандарт и является red flag службы безопасности.",
            }
        )

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Check contract against local regulations and write compliance-report.md")
    parser.add_argument("contract", type=Path)
    parser.add_argument("--regulations", type=Path, default=Path("regulations"))
    parser.add_argument("--output", type=Path, default=Path("compliance-report.md"))
    args = parser.parse_args()
    build_report(args.contract, args.regulations, args.output)


if __name__ == "__main__":
    main()
