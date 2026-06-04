from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib import request


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
OUT_FILE = ROOT / "top-managers.md"
MSK = timezone(timedelta(hours=3))


def load_webhook_url() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("BITRIX24_WEBHOOK_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("BITRIX24_WEBHOOK_URL is missing in .env")


def call_bitrix(webhook_url: str, payload: dict) -> dict:
    req = request.Request(
        f"{webhook_url}/tasks.task.list.json",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_bitrix_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def fetch_tasks(webhook_url: str, start_date: datetime, end_exclusive: datetime) -> list[dict]:
    tasks: list[dict] = []
    start = 0

    while True:
        payload = {
            "filter": {
                ">=CLOSED_DATE": start_date.isoformat(),
                "<CLOSED_DATE": end_exclusive.isoformat(),
            },
            "select": [
                "ID",
                "TITLE",
                "CREATED_DATE",
                "CLOSED_DATE",
                "RESPONSIBLE_ID",
                "responsible.name",
                "responsible.lastName",
            ],
            "order": {"CLOSED_DATE": "asc"},
            "start": start,
        }
        response = call_bitrix(webhook_url, payload)
        page = response.get("result", {}).get("tasks", [])
        if not page:
            break

        tasks.extend(page)
        start += len(page)

        total = response.get("total")
        if total is not None and start >= int(total):
            break

    return tasks


def manager_name(task: dict) -> str:
    responsible = task.get("responsible") or {}
    parts = [responsible.get("name"), responsible.get("lastName")]
    name = " ".join(part for part in parts if part)
    return name or f"Менеджер {task['responsibleId']}"


def avg_close_days(tasks: list[dict]) -> float:
    durations = [
        (parse_bitrix_dt(task["closedDate"]) - parse_bitrix_dt(task["createdDate"])).total_seconds() / 86400
        for task in tasks
    ]
    return sum(durations) / len(durations)


def main() -> None:
    webhook_url = load_webhook_url()
    start_date = datetime(2026, 4, 27, tzinfo=MSK)
    end_exclusive = datetime(2026, 5, 2, tzinfo=MSK)
    tasks = fetch_tasks(webhook_url, start_date, end_exclusive)

    grouped: dict[str, list[dict]] = defaultdict(list)
    names_by_id: dict[str, str] = {}
    for task in tasks:
        manager_id = task["responsibleId"]
        grouped[manager_id].append(task)
        names_by_id[manager_id] = manager_name(task)

    stats = []
    for manager_id, manager_tasks in grouped.items():
        stats.append(
            {
                "manager_id": manager_id,
                "manager": names_by_id[manager_id],
                "avg_days": avg_close_days(manager_tasks),
                "tasks_count": len(manager_tasks),
            }
        )

    stats.sort(key=lambda item: (item["avg_days"], -item["tasks_count"], item["manager"]))

    rows = [
        f"| {idx} | {item['manager']} | {item['manager_id']} | {item['avg_days']:.2f} | {item['tasks_count']} |"
        for idx, item in enumerate(stats, start=1)
    ]
    top_rows = [
        f"| {idx} | {item['manager']} | {item['avg_days']:.2f} | {item['tasks_count']} |"
        for idx, item in enumerate(stats[:5], start=1)
    ]
    top_names = ", ".join(item["manager"] for item in stats[:5])

    content = "\n".join(
        [
            "# Топ менеджеров по скорости закрытия задач",
            "",
            "Период: 27.04.2026 - 01.05.2026. Метрика: среднее время от создания задачи до закрытия, в днях.",
            "",
            "## Топ-5 самых быстрых",
            "",
            "| Место | Менеджер | Среднее время закрытия, дней | Закрыто задач |",
            "| ---: | --- | ---: | ---: |",
            *top_rows,
            "",
            f"Повышенный бонус в понедельник получают: {top_names}.",
            "",
            "## Полное распределение",
            "",
            "| Место | Менеджер | ID ответственного | Среднее время закрытия, дней | Закрыто задач |",
            "| ---: | --- | ---: | ---: | ---: |",
            *rows,
            "",
            f"Всего обработано закрытых задач: {len(tasks)}. Менеджеров в распределении: {len(stats)}.",
            "",
        ]
    )
    OUT_FILE.write_text(content, encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
    print(f"Fetched tasks: {len(tasks)}")
    print(f"Managers: {len(stats)}")


if __name__ == "__main__":
    main()
