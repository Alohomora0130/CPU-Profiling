from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def parse_user_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


@dataclass(frozen=True)
class SliceRecord:
    started_at: datetime
    ended_at: datetime
    perf_data_path: Path
    metadata_path: Path

    @classmethod
    def from_metadata(cls, metadata_path: Path) -> "SliceRecord":
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        started_at = parse_user_timestamp(payload["started_at"])
        ended_at = parse_user_timestamp(payload["ended_at"])
        return cls(
            started_at=started_at,
            ended_at=ended_at,
            perf_data_path=Path(payload["perf_data_path"]),
            metadata_path=metadata_path,
        )

    def contains(self, timestamp: datetime) -> bool:
        return self.started_at <= timestamp <= self.ended_at

    def distance_seconds(self, timestamp: datetime) -> float:
        if self.contains(timestamp):
            return 0.0
        if timestamp < self.started_at:
            return (self.started_at - timestamp).total_seconds()
        return (timestamp - self.ended_at).total_seconds()


def discover_slices(data_dir: Path) -> list[SliceRecord]:
    records = [SliceRecord.from_metadata(path) for path in sorted(data_dir.glob("*.json"))]
    return sorted(records, key=lambda item: item.started_at)


def find_best_slice(
    data_dir: Path,
    timestamp: datetime,
    nearest_within_seconds: int | None = 300,
) -> SliceRecord:
    slices = discover_slices(data_dir)
    if not slices:
        raise FileNotFoundError(f"no profiling slices found in {data_dir}")

    for record in slices:
        if record.contains(timestamp):
            return record

    best = min(slices, key=lambda item: item.distance_seconds(timestamp))
    if nearest_within_seconds is None:
        return best

    distance = best.distance_seconds(timestamp)
    if distance > nearest_within_seconds:
        raise FileNotFoundError(
            f"no profiling slice covers {timestamp.isoformat()} "
            f"within {nearest_within_seconds} seconds"
        )
    return best
