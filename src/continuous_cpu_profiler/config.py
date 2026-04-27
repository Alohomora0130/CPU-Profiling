from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProfilerConfig:
    data_dir: Path
    slice_seconds: int = 60
    retention_hours: int = 72
    frequency_hz: int = 99
    event: str = "cpu-clock"
    call_graph: str = "fp"
    perf_binary: str = "perf"
    flamegraph_dir: Path | None = None
    target: str = "system"
    sleep_binary: str = "sleep"
    extra_perf_args: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, payload: dict) -> "ProfilerConfig":
        data_dir = Path(payload["data_dir"]).expanduser()
        flamegraph_dir = payload.get("flamegraph_dir")
        target = payload.get("target", "system")
        extra_perf_args = tuple(payload.get("extra_perf_args", ()))

        config = cls(
            data_dir=data_dir,
            slice_seconds=int(payload.get("slice_seconds", 60)),
            retention_hours=int(payload.get("retention_hours", 72)),
            frequency_hz=int(payload.get("frequency_hz", 99)),
            event=str(payload.get("event", "cpu-clock")),
            call_graph=str(payload.get("call_graph", "fp")),
            perf_binary=str(payload.get("perf_binary", "perf")),
            flamegraph_dir=Path(flamegraph_dir).expanduser() if flamegraph_dir else None,
            target=str(target),
            sleep_binary=str(payload.get("sleep_binary", "sleep")),
            extra_perf_args=extra_perf_args,
        )
        config.validate()
        return config

    @classmethod
    def load(cls, config_path: str | Path) -> "ProfilerConfig":
        raw = json.loads(Path(config_path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    def validate(self) -> None:
        if self.slice_seconds <= 0:
            raise ValueError("slice_seconds must be > 0")
        if self.retention_hours <= 0:
            raise ValueError("retention_hours must be > 0")
        if self.frequency_hz <= 0:
            raise ValueError("frequency_hz must be > 0")
        if self.call_graph not in {"fp", "dwarf", "lbr"}:
            raise ValueError("call_graph must be one of: fp, dwarf, lbr")
        if self.target != "system" and not self.target.startswith("pid:"):
            raise ValueError("target must be 'system' or 'pid:<PID>'")

    def perf_scope_args(self) -> list[str]:
        if self.target == "system":
            return ["-a"]
        _, pid = self.target.split(":", 1)
        return ["-p", pid]

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def to_public_dict(self) -> dict:
        return {
            "data_dir": str(self.data_dir),
            "slice_seconds": self.slice_seconds,
            "retention_hours": self.retention_hours,
            "frequency_hz": self.frequency_hz,
            "event": self.event,
            "call_graph": self.call_graph,
            "perf_binary": self.perf_binary,
            "flamegraph_dir": str(self.flamegraph_dir) if self.flamegraph_dir else None,
            "target": self.target,
            "sleep_binary": self.sleep_binary,
            "extra_perf_args": list(self.extra_perf_args),
        }
