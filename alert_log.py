"""Demo alarmlarını yerel JSONL dosyasına yaz ve oku."""

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
import json


LOG_FILE = Path(__file__).resolve().parent / "logs" / "alerts.jsonl"
_LOCK = Lock()


def record_alerts(events: list[dict]) -> None:
    if not events:
        return
    LOG_FILE.parent.mkdir(exist_ok=True)
    with _LOCK, LOG_FILE.open("a", encoding="utf-8") as output:
        for event in events:
            event.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat(timespec="seconds"))
            output.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")


def read_alerts(run_id: str | None = None, limit: int = 200) -> list[dict]:
    if not LOG_FILE.is_file():
        return []
    with _LOCK, LOG_FILE.open("r", encoding="utf-8") as source:
        lines = source.readlines()
    events = [json.loads(line) for line in lines if line.strip()]
    if run_id is not None:
        events = [event for event in events if event.get("run_id") == run_id]
    return events[-limit:][::-1]
