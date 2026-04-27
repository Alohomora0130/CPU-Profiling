from __future__ import annotations

import argparse
import json
from pathlib import Path

from .collector import ContinuousProfiler
from .config import ProfilerConfig
from .query import discover_slices, find_best_slice, parse_user_timestamp
from .render import render_flamegraph


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Linux continuous CPU profiler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="run perf capture forever")
    collect.add_argument("--config", required=True, help="path to config json")

    once = subparsers.add_parser("once", help="capture one profiling slice")
    once.add_argument("--config", required=True, help="path to config json")

    query = subparsers.add_parser("query", help="render flamegraph for a timestamp")
    query.add_argument("--config", required=True, help="path to config json")
    query.add_argument("--at", required=True, help="ISO-8601 timestamp")
    query.add_argument("--nearest-seconds", type=int, default=300)
    query.add_argument("--output-dir", required=True, help="directory for outputs")
    query.add_argument("--title", help="optional flamegraph title")

    list_cmd = subparsers.add_parser("list", help="list available profiling slices")
    list_cmd.add_argument("--config", required=True, help="path to config json")
    list_cmd.add_argument("--limit", type=int, default=20)

    return parser


def _load_config(config_path: str) -> ProfilerConfig:
    return ProfilerConfig.load(config_path)


def handle_collect(args: argparse.Namespace) -> int:
    profiler = ContinuousProfiler(_load_config(args.config))
    profiler.run_forever()
    return 0


def handle_once(args: argparse.Namespace) -> int:
    profiler = ContinuousProfiler(_load_config(args.config))
    result = profiler.capture_once()
    print(
        json.dumps(
            {
                "started_at": result.started_at.isoformat(),
                "ended_at": result.ended_at.isoformat(),
                "perf_data_path": str(result.perf_data_path),
                "metadata_path": str(result.metadata_path),
            },
            indent=2,
        )
    )
    return 0


def handle_query(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    timestamp = parse_user_timestamp(args.at)
    record = find_best_slice(
        config.data_dir,
        timestamp,
        nearest_within_seconds=args.nearest_seconds,
    )
    rendered = render_flamegraph(
        perf_binary=config.perf_binary,
        perf_data_path=record.perf_data_path,
        output_dir=Path(args.output_dir),
        flamegraph_dir=config.flamegraph_dir,
        title=args.title or f"CPU Profile @ {timestamp.isoformat()}",
    )
    print(
        json.dumps(
            {
                "query_timestamp": timestamp.isoformat(),
                "matched_slice_started_at": record.started_at.isoformat(),
                "matched_slice_ended_at": record.ended_at.isoformat(),
                "perf_data_path": str(record.perf_data_path),
                "folded_path": str(rendered["folded"]),
                "svg_path": str(rendered["svg"]),
            },
            indent=2,
        )
    )
    return 0


def handle_list(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    rows = []
    for record in discover_slices(config.data_dir)[-args.limit :]:
        rows.append(
            {
                "started_at": record.started_at.isoformat(),
                "ended_at": record.ended_at.isoformat(),
                "perf_data_path": str(record.perf_data_path),
                "metadata_path": str(record.metadata_path),
            }
        )
    print(json.dumps(rows, indent=2))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "collect":
        return handle_collect(args)
    if args.command == "once":
        return handle_once(args)
    if args.command == "query":
        return handle_query(args)
    if args.command == "list":
        return handle_list(args)

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
