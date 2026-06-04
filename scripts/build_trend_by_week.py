from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib import request


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
OUT_FILE = ROOT / "trend-by-week.md"
MSK = timezone(timedelta(hours=3))


def load_webhook_url() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("BITRIX24_WEBHOOK_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("BITRIX24_WEBHOOK_URL is missing in .env")


def call_bitrix(webhook_url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{webhook_url}/tasks.task.list.json",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_bitrix_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def fetch_closed_tasks(webhook_url: str, start_date: datetime, end_exclusive: datetime) -> list[dict]:
    tasks: list[dict] = []
    start = 0

    while True:
        payload = {
            "filter": {
                ">=CLOSED_DATE": start_date.isoformat(),
                "<CLOSED_DATE": end_exclusive.isoformat(),
            },
            "select": ["ID", "TITLE", "CREATED_DATE", "CLOSED_DATE"],
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


def average_days(tasks: list[dict]) -> float | None:
    durations = []
    for task in tasks:
        created = parse_bitrix_dt(task["createdDate"])
        closed = parse_bitrix_dt(task["closedDate"])
        durations.append((closed - created).total_seconds() / 86400)

    if not durations:
        return None

    return sum(durations) / len(durations)


def format_delta(value: float | None, baseline: float | None) -> str:
    if value is None or baseline is None:
        return "n/a"

    delta = value - baseline
    if abs(delta) < 0.005:
        return "0.00"

    return f"{delta:+.2f}"


def main() -> None:
    webhook_url = load_webhook_url()
    start_date = datetime(2026, 3, 30, tzinfo=MSK)
    end_exclusive = datetime(2026, 5, 2, tzinfo=MSK)
    tasks = fetch_closed_tasks(webhook_url, start_date, end_exclusive)

    weeks = [
        (datetime(2026, 3, 30, tzinfo=MSK), datetime(2026, 4, 6, tzinfo=MSK)),
        (datetime(2026, 4, 6, tzinfo=MSK), datetime(2026, 4, 13, tzinfo=MSK)),
        (datetime(2026, 4, 13, tzinfo=MSK), datetime(2026, 4, 20, tzinfo=MSK)),
        (datetime(2026, 4, 20, tzinfo=MSK), datetime(2026, 4, 27, tzinfo=MSK)),
        (datetime(2026, 4, 27, tzinfo=MSK), datetime(2026, 5, 2, tzinfo=MSK)),
    ]

    rows = []
    for week_start, week_end in weeks:
        week_tasks = [
            task
            for task in tasks
            if week_start <= parse_bitrix_dt(task["closedDate"]) < week_end
        ]
        rows.append((week_start, week_end - timedelta(days=1), average_days(week_tasks), len(week_tasks)))

    baseline = rows[0][2]
    markdown_rows = []
    for week_start, week_end, avg, count in rows:
        range_text = f"{week_start:%d.%m.%Y} - {week_end:%d.%m.%Y}"
        avg_text = "n/a" if avg is None else f"{avg:.2f}"
        markdown_rows.append(
            f"| {range_text} | {avg_text} | {format_delta(avg, baseline)} | {count} |"
        )

    values = [row[2] for row in rows if row[2] is not None]
    trend_sentence = (
        "Во второй неделе показатель почти не изменился, а затем среднее время закрытия последовательно снижалось."
        if len(values) == 5 and values[1] >= values[0] and values[2] < values[0]
        else "По пяти неделям не видно устойчивого снижения относительно первой недели."
    )
    last_sentence = (
        f"К последней неделе показатель составил {values[-1]:.2f} дня против {values[0]:.2f} дня на первой неделе."
        if len(values) >= 2
        else "Данных недостаточно для сравнения с первой неделей."
    )

    content = "\n".join(
        [
            "# Тренд времени закрытия задач по неделям",
            "",
            "| Неделя | Среднее время закрытия, дней | Изменение к первой неделе, дней | Закрыто задач |",
            "| --- | ---: | ---: | ---: |",
            *markdown_rows,
            "",
            f"{trend_sentence} {last_sentence}",
            "",
        ]
    )
    OUT_FILE.write_text(content, encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
    print(f"Fetched tasks: {len(tasks)}")


if __name__ == "__main__":
    main()
