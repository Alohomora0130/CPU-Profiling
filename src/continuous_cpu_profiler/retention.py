from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_utc_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def prune_old_slices(data_dir: Path, retention_hours: int) -> list[Path]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
    deleted: list[Path] = []

    for meta_file in sorted(data_dir.glob("*.json")):
        payload = json.loads(meta_file.read_text(encoding="utf-8"))
        ended_at = parse_utc_timestamp(payload["ended_at"])
        if ended_at >= cutoff:
            continue

        data_file = Path(payload["perf_data_path"])
        if data_file.exists():
            data_file.unlink()
            deleted.append(data_file)

        meta_file.unlink()
        deleted.append(meta_file)

    return deleted
