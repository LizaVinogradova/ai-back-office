from __future__ import annotations

import base64
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib import parse, request


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
TREND_FILE = ROOT / "trend-by-week.md"
OUT_FILE = ROOT / "real-effect.md"

MSK = timezone(timedelta(hours=3))
ONEC_BASE = "https://roz.lms.robotsatwork.ai/mock-1c/kpop_back_office/odata/standard.odata"
ONEC_LOGIN = "kpop_reader"
ONEC_ACT_RESOURCE = "Document_\u0410\u043a\u0442\u0412\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u043d\u044b\u0445\u0420\u0430\u0431\u043e\u0442"


def load_webhook_url() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("BITRIX24_WEBHOOK_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("BITRIX24_WEBHOOK_URL is missing in .env")


def load_onec_password(webhook_url: str) -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("ONEC_PASSWORD="):
            return line.split("=", 1)[1].strip()
    return webhook_url.rstrip("/").split("/")[-1]


def parse_bitrix_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def parse_onec_dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=MSK)


def call_bitrix(webhook_url: str, payload: dict) -> dict:
    req = request.Request(
        f"{webhook_url}/tasks.task.list.json",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_bitrix_tasks(webhook_url: str, start_date: datetime, end_exclusive: datetime) -> list[dict]:
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


def call_onec(password: str, params: dict) -> dict:
    query = parse.urlencode(params, safe="(),' ")
    url = f"{ONEC_BASE}/{parse.quote(ONEC_ACT_RESOURCE)}?{query}"
    auth = base64.b64encode(f"{ONEC_LOGIN}:{password}".encode("utf-8")).decode("ascii")
    req = request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_onec_acts(password: str, start_date: datetime, end_inclusive: datetime) -> list[dict]:
    acts: list[dict] = []
    skip = 0
    top = 100
    while True:
        params = {
            "$format": "json",
            "$filter": (
                "Posted eq true "
                f"and Date ge datetime'{start_date:%Y-%m-%dT%H:%M:%S}' "
                f"and Date le datetime'{end_inclusive:%Y-%m-%dT%H:%M:%S}'"
            ),
            "$select": "Ref_Key,Number,Date,Posted,Контрагент,Проект,СуммаДокумента,Основание",
            "$orderby": "Date asc",
            "$top": str(top),
            "$skip": str(skip),
        }
        page = call_onec(password, params).get("value", [])
        if not page:
            break
        acts.extend(page)
        if len(page) < top:
            break
        skip += top
    return acts


def parse_trend_bitrix_avgs() -> dict[str, float]:
    avgs: dict[str, float] = {}
    for line in TREND_FILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\| (\d{2}\.\d{2}\.\d{4} - \d{2}\.\d{2}\.\d{4}) \| ([\d.]+) \|", line)
        if match:
            avgs[match.group(1)] = float(match.group(2))
    if len(avgs) != 5:
        raise RuntimeError("Could not parse five Bitrix weekly averages from trend-by-week.md")
    return avgs


def avg(values: list[float]) -> float | None:
    return None if not values else sum(values) / len(values)


def fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def main() -> None:
    webhook_url = load_webhook_url()
    onec_password = load_onec_password(webhook_url)

    weeks = [
        (datetime(2026, 3, 30, tzinfo=MSK), datetime(2026, 4, 6, tzinfo=MSK)),
        (datetime(2026, 4, 6, tzinfo=MSK), datetime(2026, 4, 13, tzinfo=MSK)),
        (datetime(2026, 4, 13, tzinfo=MSK), datetime(2026, 4, 20, tzinfo=MSK)),
        (datetime(2026, 4, 20, tzinfo=MSK), datetime(2026, 4, 27, tzinfo=MSK)),
        (datetime(2026, 4, 27, tzinfo=MSK), datetime(2026, 5, 2, tzinfo=MSK)),
    ]

    bitrix_tasks = fetch_bitrix_tasks(webhook_url, weeks[0][0], weeks[-1][1])
    tasks_by_id = {task["id"]: task for task in bitrix_tasks}
    acts = fetch_onec_acts(
        onec_password,
        datetime(2026, 3, 30, tzinfo=MSK),
        datetime(2026, 5, 15, 23, 59, 59, tzinfo=MSK),
    )

    acts_by_task: dict[str, list[dict]] = defaultdict(list)
    for act in acts:
        match = re.search(r"task:(\d+)", str(act.get("Основание", "")))
        if match:
            acts_by_task[match.group(1)].append(act)

    real_durations_by_week: dict[str, list[float]] = defaultdict(list)
    linked_task_count_by_week: dict[str, int] = defaultdict(int)
    for week_start, week_end in weeks:
        week_label = f"{week_start:%d.%m.%Y} - {(week_end - timedelta(days=1)):%d.%m.%Y}"
        for task in bitrix_tasks:
            closed = parse_bitrix_dt(task["closedDate"])
            if not (week_start <= closed < week_end):
                continue
            task_acts = acts_by_task.get(task["id"], [])
            if not task_acts:
                continue
            # If a task has several acts, the latest posted act is the real final close.
            act = max(task_acts, key=lambda item: parse_onec_dt(item["Date"]))
            created = parse_bitrix_dt(task["createdDate"])
            real_closed = parse_onec_dt(act["Date"])
            real_durations_by_week[week_label].append((real_closed - created).total_seconds() / 86400)
            linked_task_count_by_week[week_label] += 1

    bitrix_avgs = parse_trend_bitrix_avgs()
    rows = []
    real_values = []
    bitrix_values = []
    for week_start, week_end in weeks:
        week_label = f"{week_start:%d.%m.%Y} - {(week_end - timedelta(days=1)):%d.%m.%Y}"
        bitrix_avg = bitrix_avgs[week_label]
        real_avg = avg(real_durations_by_week[week_label])
        diff = None if real_avg is None else real_avg - bitrix_avg
        if real_avg is not None:
            real_values.append(real_avg)
            bitrix_values.append(bitrix_avg)
        rows.append(
            f"| {week_label} | {bitrix_avg:.2f} | {fmt(real_avg)} | {fmt(diff)} | {linked_task_count_by_week[week_label]} |"
        )

    avg_gap = avg([real - bitrix for real, bitrix in zip(real_values, bitrix_values)])
    tail_sentence = (
        f"По актам 1С закрытие в среднем позже Bitrix на {avg_gap:.2f} дня: фактическое оформление документов добавляет заметный хвост."
        if avg_gap is not None and avg_gap > 0
        else "По актам 1С нет заметного отставания от Bitrix по среднему времени закрытия."
    )
    trend_sentence = (
        "Тренд улучшения сохраняется: к последней неделе реальная скорость по 1С тоже ниже стартовой."
        if len(real_values) == 5 and real_values[-1] < real_values[0]
        else "По реальным актам тренд менее ровный, чем по Bitrix."
    )

    content = "\n".join(
        [
            "# Реальный эффект по актам 1С",
            "",
            "Акты 1С взяты за период 30.03.2026 - 15.05.2026 и связаны с задачами Bitrix по полю `Основание` в формате `task:<id>`.",
            "",
            "| Неделя | Среднее по Bitrix, дней | Реальное по 1С, дней | Разница 1С - Bitrix, дней | Связано актов/задач |",
            "| --- | ---: | ---: | ---: | ---: |",
            *rows,
            "",
            f"{tail_sentence} {trend_sentence}",
            "",
            f"Проверка данных: задач Bitrix за пять недель — {len(bitrix_tasks)}, актов 1С за период с запасом — {len(acts)}, связанных задач — {sum(linked_task_count_by_week.values())}.",
            "",
        ]
    )
    OUT_FILE.write_text(content, encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
    print(f"Bitrix tasks: {len(bitrix_tasks)}")
    print(f"1C acts: {len(acts)}")
    print(f"Linked tasks: {sum(linked_task_count_by_week.values())}")


if __name__ == "__main__":
    main()
