from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from continuous_cpu_profiler.query import find_best_slice, parse_user_timestamp


def _write_meta(path: Path, started_at: str, ended_at: str, data_name: str) -> None:
    payload = {
        "started_at": started_at,
        "ended_at": ended_at,
        "perf_data_path": str(path.parent / data_name),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class QueryTests(unittest.TestCase):
    def test_parse_user_timestamp_defaults_to_utc(self) -> None:
        result = parse_user_timestamp("2026-04-27T10:12:00")
        self.assertEqual(result, datetime(2026, 4, 27, 10, 12, 0, tzinfo=timezone.utc))

    def test_find_best_slice_prefers_covering_slice(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            _write_meta(
                tmp_path / "20260427T101100Z.json",
                "2026-04-27T10:11:00+00:00",
                "2026-04-27T10:12:00+00:00",
                "20260427T101100Z.data",
            )
            _write_meta(
                tmp_path / "20260427T101200Z.json",
                "2026-04-27T10:12:00+00:00",
                "2026-04-27T10:13:00+00:00",
                "20260427T101200Z.data",
            )

            record = find_best_slice(
                tmp_path,
                parse_user_timestamp("2026-04-27T10:12:30+00:00"),
                nearest_within_seconds=10,
            )

            self.assertEqual(record.perf_data_path.name, "20260427T101200Z.data")


if __name__ == "__main__":
    unittest.main()
