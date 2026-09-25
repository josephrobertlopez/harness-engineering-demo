"""Run track 50 end to end with Claude Haiku as the developer.

    python run_trial.py <out-dir> [01 02 03] [--model claude-haiku-4-5]

Two agents, both Haiku by default:

- the **developer**: one Claude Code session per exercise, driven only
  through the /fidelity:* slash commands start.py installs -- the same
  commands a learner types;
- the **product owner**: a fresh, tool-less call per batch of questions,
  given stakeholder-answers.md and told to answer only what was asked.

The developer's workspace is created by start.py; the stakeholder file is
then moved out of its reach. Every tool call is logged (stream-json), and
the report flags any read of a stakeholder file or a solution/ path, so a
green result can be audited rather than trusted.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

# trials/<run>/run_trial.py -> the repo root, unless TRACK50_REPO points at a snapshot.
REPO = Path(os.environ.get("TRACK50_REPO", Path(__file__).resolve().parents[2]))
TRACK = REPO / "tutorials" / "50-spec-fidelity"
CHANGE_IDS = {"01": "add-fx-convert", "02": "add-help-chat", "03": "add-cli-mcp"}
EXERCISE_NAMES = {"01": "ops-1432", "02": "sup-88", "03": "devx-311"}
MAX_INTERVIEW_ROUNDS = 5
DEV_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]

# The child must not inherit this session's identity, or its transcript
# lands in ours.
ISOLATE = [
    "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_REMOTE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
    "CLAUDE_CODE_SYNC_SESSION_REFS", "CLAUDE_CODE_TEE_SDK_STDOUT",
]

PO_SYSTEM = """You are the product owner for a software ticket. A developer is
interviewing you. Your knowledge is exactly the document below -- nothing else.

Rules:
- Answer only the questions asked, one numbered answer per question, in plain
  prose. Keep the question numbers the developer used.
- Use only facts from the document. Quote exact values (numbers, codes, strings,
  ids, commands) verbatim when a question asks for them.
- If the document does not decide something, answer exactly:
  "No decision - treat it as a non-goal."
- Answer each question completely: if it asks for a list ("which error codes",
  "which tools"), give every item the document lists for it.
- Never volunteer information a question did not ask for, even if relevant.
- Do not mention that you are reading a document.

<document>
{answers}
</document>"""


def env() -> dict[str, str]:
    e = dict(os.environ)
    for key in ISOLATE:
        e.pop(key, None)
    e["OPENSPEC_TELEMETRY"] = "0"
    return e


class Dev:
    """One developer session, resumed across steps."""

    def __init__(self, ws: Path, log: Path, model: str):
        self.ws, self.log, self.model = ws, log, model
        self.session = str(uuid.uuid4())
        self.started = False
        self.cost = 0.0

    def run(self, prompt: str, step: str, timeout: int = 1800) -> str:
        cmd = [
            "claude", "-p", prompt, "--model", self.model,
            "--output-format", "stream-json", "--verbose",
            "--permission-mode", "acceptEdits",
            "--allowedTools", *DEV_TOOLS,
        ]
        cmd += ["--resume", self.session] if self.started else ["--session-id", self.session]
        self.started = True
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=self.ws, env=env(), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
        events = [json.loads(line) for line in proc.stdout.splitlines() if line.strip().startswith("{")]
        with self.log.open("a", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps({"step": step, **ev}) + "\n")
        result = next((ev for ev in reversed(events) if ev.get("type") == "result"), {})
        # Cumulative for a resumed session, so the latest value is the total.
        self.cost = result.get("total_cost_usd", self.cost) or self.cost
        text = result.get("result", "") or proc.stderr[-2000:]
        print(f"    [{step}] {time.time() - t0:5.0f}s  ${self.cost:.3f} total", flush=True)
        return text


def product_owner(answers: str, questions: str, model: str) -> tuple[str, float]:
    proc = subprocess.run(
        ["claude", "-p", f"The developer asks:\n\n{questions}\n\nAnswer as the product owner.",
         "--model", model, "--system-prompt", PO_SYSTEM.format(answers=answers),
         "--tools", "", "--output-format", "json"],
        cwd="/tmp", env=env(), capture_output=True, text=True, encoding="utf-8", timeout=600,
    )
    data = json.loads(proc.stdout)
    return data.get("result", ""), data.get("total_cost_usd", 0.0) or 0.0


def judge(ws: Path, python: str, stage: str = "all") -> tuple[bool, str]:
    proc = subprocess.run([python, str(TRACK / "spec_fidelity.py"), str(ws), "--stage", stage],
                          capture_output=True, text=True, encoding="utf-8")
    return proc.returncode == 0, proc.stdout


def run_exercise(num: str, out: Path, model: str, python: str) -> dict:
    name = EXERCISE_NAMES[num]
    ws = out / name
    subprocess.run([python, str(TRACK / "start.py"), num, str(ws)], check=True, capture_output=True)
    # Out of the developer's reach: not in the workspace, not next to it.
    hidden = out.parent / f".po-{out.name}"
    hidden.mkdir(exist_ok=True)
    answers_path = hidden / f"{name}.stakeholder-answers.md"
    shutil.move(str(out / f"{name}.stakeholder-answers.md"), answers_path)
    answers = answers_path.read_text(encoding="utf-8")

    log = out / f"{name}.transcript.jsonl"
    dev = Dev(ws, log, model)
    po_cost = 0.0
    record: dict = {"exercise": num, "workspace": name, "steps": []}

    def step(label, prompt, **kw):
        text = dev.run(prompt, label, **kw)
        record["steps"].append({"step": label, "prompt": prompt, "reply": text})
        return text

    def interview(first_prompt: str, label: str) -> None:
        nonlocal po_cost
        reply = step(f"{label}-1", first_prompt)
        for rnd in range(2, MAX_INTERVIEW_ROUNDS + 2):
            if "INTERVIEW COMPLETE" in reply:
                return
            answer, c = product_owner(answers, reply, model)
            po_cost += c
            record["steps"].append({"step": f"{label}-po-{rnd - 1}", "reply": answer})
            reply = step(f"{label}-{rnd}", f"/fidelity:interrogate {answer}")

    print(f"== {num} {name}", flush=True)
    interview("/fidelity:interrogate", "interrogate")
    def prd_until_green(label: str, prompt: str) -> None:
        # The prd command stops and asks when a fact was never pinned down.
        # Every such stop goes back to the product owner -- the first version
        # of this harness routed only the first one, and a run failed on a
        # question Haiku asked correctly and nobody answered.
        nonlocal po_cost
        reply = step(label, prompt)
        for attempt in range(1, 4):
            ok_prd, _ = judge(ws, python, stage="prd")
            if ok_prd:
                return
            answer, c = product_owner(answers, reply, model)
            po_cost += c
            record["steps"].append({"step": f"{label}-po-{attempt}", "reply": answer})
            step(f"{label}-answers-{attempt}", f"/fidelity:interrogate {answer}")
            reply = step(f"{label}-retry-{attempt}", "/fidelity:prd")

    prd_until_green("prd", "/fidelity:prd")
    step("review-prd", "/fidelity:review-prd")
    prd_until_green("prd-review", "/fidelity:prd Apply the review findings that need only a rewrite of prd.md. "
                                  "Do not invent answers for findings that need a product-owner decision; list them.")
    step("propose", f"/fidelity:propose {CHANGE_IDS[num]}")
    step("build", "/fidelity:build", timeout=3600)
    step("judge", "/fidelity:judge")
    step("enforce", "/fidelity:enforce")

    ok, report = judge(ws, python)
    record.update(ok=ok, judge=report, dev_cost=round(dev.cost, 4), po_cost=round(po_cost, 4),
                  session=dev.session)
    (out / f"{name}.judge.txt").write_text(report, encoding="utf-8")
    (out / f"{name}.steps.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(report.splitlines()[-1], flush=True)
    return record


def audit(out: Path) -> list[str]:
    """Tool calls that touched something the developer should never see."""
    flags = []
    for log in sorted(out.glob("*.transcript.jsonl")):
        for line in log.read_text(encoding="utf-8").splitlines():
            ev = json.loads(line)
            if ev.get("type") != "assistant":
                continue
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") != "tool_use":
                    continue
                blob = json.dumps(block.get("input", {}))
                if "stakeholder" in blob or "/solution" in blob or "harness-engineering-demo/tutorials" in blob and "spec_fidelity.py" not in blob:
                    flags.append(f"{log.name} [{ev['step']}] {block['name']}: {blob[:200]}")
    return flags


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    p.add_argument("exercises", nargs="*", default=["01", "02", "03"])
    p.add_argument("--model", default="claude-haiku-4-5")
    p.add_argument("--python", default=sys.executable)
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    results = [run_exercise(n, out, a.model, a.python) for n in a.exercises]
    flags = audit(out)
    summary = {
        "model": a.model,
        "results": [{k: r[k] for k in ("exercise", "workspace", "ok", "dev_cost", "po_cost")} for r in results],
        "leak_flags": flags,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
