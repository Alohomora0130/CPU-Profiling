from __future__ import annotations

import json
import os
import subprocess
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import ProfilerConfig
from .retention import prune_old_slices


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_slice_stem(started_at: datetime) -> str:
    return started_at.strftime("%Y%m%dT%H%M%SZ")


class FileLock(AbstractContextManager):
    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        self.handle = None

    def __enter__(self) -> "FileLock":
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.lock_path.open("a+b")
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.handle is None:
            return
        if os.name == "nt":
            import msvcrt

            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


@dataclass
class CaptureResult:
    perf_data_path: Path
    metadata_path: Path
    started_at: datetime
    ended_at: datetime
    command: list[str]


class ContinuousProfiler:
    def __init__(self, config: ProfilerConfig) -> None:
        self.config = config

    def build_perf_command(self, output_file: Path) -> list[str]:
        command = [
            self.config.perf_binary,
            "record",
            "-F",
            str(self.config.frequency_hz),
            "-e",
            self.config.event,
            "-g",
            "--call-graph",
            self.config.call_graph,
            "-o",
            str(output_file),
        ]
        command.extend(self.config.perf_scope_args())
        command.extend(self.config.extra_perf_args)
        command.extend(["--", self.config.sleep_binary, str(self.config.slice_seconds)])
        return command

    def capture_once(self) -> CaptureResult:
        self.config.ensure_directories()
        started_at = utc_now()
        stem = build_slice_stem(started_at)
        temp_perf_data = self.config.data_dir / f"{stem}.data.partial"
        final_perf_data = self.config.data_dir / f"{stem}.data"
        metadata_file = self.config.data_dir / f"{stem}.json"
        command = self.build_perf_command(temp_perf_data)

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        ended_at = utc_now()

        if completed.returncode != 0:
            if temp_perf_data.exists():
                temp_perf_data.unlink()
            raise RuntimeError(
                "perf record failed with exit code "
                f"{completed.returncode}: {completed.stderr.strip()}"
            )

        temp_perf_data.replace(final_perf_data)
        payload = {
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "perf_data_path": str(final_perf_data),
            "metadata_path": str(metadata_file),
            "command": command,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
        metadata_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return CaptureResult(
            perf_data_path=final_perf_data,
            metadata_path=metadata_file,
            started_at=started_at,
            ended_at=ended_at,
            command=command,
        )

    def run_forever(self) -> None:
        self.config.ensure_directories()
        lock_path = self.config.data_dir / ".collector.lock"
        with FileLock(lock_path):
            while True:
                try:
                    self.capture_once()
                    prune_old_slices(self.config.data_dir, self.config.retention_hours)
                except KeyboardInterrupt:
                    raise
                except Exception as exc:  # pragma: no cover - production safety net
                    print(f"[collector] capture failed: {exc}", flush=True)
                    time.sleep(5)
