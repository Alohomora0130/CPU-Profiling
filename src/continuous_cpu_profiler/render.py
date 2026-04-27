from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _resolve_flamegraph_script(flamegraph_dir: Path, script_name: str) -> Path:
    script_path = flamegraph_dir / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"missing FlameGraph script: {script_path}")
    return script_path


def render_flamegraph(
    perf_binary: str,
    perf_data_path: Path,
    output_dir: Path,
    flamegraph_dir: Path | None,
    title: str | None = None,
) -> dict[str, Path | None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    folded_path = output_dir / f"{perf_data_path.stem}.folded"
    svg_path = output_dir / f"{perf_data_path.stem}.svg"

    if shutil.which(perf_binary) is None:
        raise FileNotFoundError(f"perf binary not found: {perf_binary}")

    if flamegraph_dir is None:
        raise FileNotFoundError("flamegraph_dir is not configured")

    stackcollapse = _resolve_flamegraph_script(flamegraph_dir, "stackcollapse-perf.pl")
    flamegraph = _resolve_flamegraph_script(flamegraph_dir, "flamegraph.pl")

    perf_script = subprocess.Popen(
        [perf_binary, "script", "-f", "-i", str(perf_data_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stackcollapse_proc = subprocess.Popen(
        ["perl", str(stackcollapse)],
        stdin=perf_script.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if perf_script.stdout is not None:
        perf_script.stdout.close()

    folded_output, stackcollapse_stderr = stackcollapse_proc.communicate()
    perf_stderr = perf_script.communicate()[1]

    if perf_script.returncode not in (0, None):
        raise RuntimeError(f"perf script failed: {perf_stderr.strip()}")
    if stackcollapse_proc.returncode != 0:
        raise RuntimeError(f"stackcollapse-perf.pl failed: {stackcollapse_stderr.strip()}")

    folded_path.write_text(folded_output, encoding="utf-8")

    flamegraph_cmd = ["perl", str(flamegraph)]
    if title:
        flamegraph_cmd.extend(["--title", title])

    with folded_path.open("r", encoding="utf-8") as folded_stream:
        flamegraph_proc = subprocess.run(
            flamegraph_cmd,
            stdin=folded_stream,
            capture_output=True,
            text=True,
            check=False,
        )

    if flamegraph_proc.returncode != 0:
        raise RuntimeError(f"flamegraph.pl failed: {flamegraph_proc.stderr.strip()}")

    svg_path.write_text(flamegraph_proc.stdout, encoding="utf-8")
    return {"folded": folded_path, "svg": svg_path}
