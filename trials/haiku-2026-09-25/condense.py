"""Condense a trial transcript (stream-json) into a readable tool-call log.

    python condense.py <run-dir> <out-dir>

Writes <out-dir>/<name>/tool-calls.md and copies the artifacts a reader
needs: interview.md, prd.md, openspec/changes, impl/ (no caches), the judge
report and the per-step replies.
"""

import json
import shutil
import sys
from pathlib import Path


def short(inp: dict) -> str:
    for key in ("command", "file_path", "pattern", "path", "description"):
        if key in inp:
            return f"{key}={str(inp[key])[:140]!r}"
    return json.dumps(inp)[:140]


def condense(run: Path, out: Path) -> None:
    for transcript in sorted(run.glob("*.transcript.jsonl")):
        name = transcript.name.split(".")[0]
        dest = out / name
        dest.mkdir(parents=True, exist_ok=True)
        lines = [f"# Tool calls — {name}", "", "| step | tool | input |", "|---|---|---|"]
        denials = []
        for raw in transcript.read_text(encoding="utf-8").splitlines():
            ev = json.loads(raw)
            if ev.get("type") == "assistant":
                for block in ev.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use":
                        cell = short(block.get("input", {})).replace("|", "\\|").replace("\n", " ")
                        lines.append(f"| {ev['step']} | {block['name']} | `{cell}` |")
            if ev.get("type") == "result":
                for d in ev.get("permission_denials", []) or []:
                    denials.append(f"- {ev['step']}: {d.get('tool_name')} {json.dumps(d.get('tool_input', {}))[:160]}")
        if denials:
            lines += ["", "## Permission denials", "", *denials]
        (dest / "tool-calls.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

        ws = run / name
        for item in ("interview.md", "prd.md"):
            if (ws / item).is_file():
                shutil.copyfile(ws / item, dest / item)
        for sub in ("openspec/changes", "impl"):
            if (ws / sub).is_dir():
                shutil.copytree(ws / sub, dest / sub, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for extra in (f"{name}.judge.txt", f"{name}.steps.json"):
            if (run / extra).is_file():
                shutil.copyfile(run / extra, dest / extra.split(".", 1)[1])


if __name__ == "__main__":
    condense(Path(sys.argv[1]), Path(sys.argv[2]))
