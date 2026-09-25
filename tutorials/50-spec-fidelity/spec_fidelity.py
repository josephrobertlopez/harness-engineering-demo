"""The deterministic half of the fidelity judge for track 50.

    python tutorials/50-spec-fidelity/spec_fidelity.py <exercise-dir>
    python tutorials/50-spec-fidelity/spec_fidelity.py <exercise-dir> --stage prd
    python tutorials/50-spec-fidelity/spec_fidelity.py <exercise-dir>/solution

It judges three artifacts against each other, in the order they are written:

    ticket.md  --(interrogate)-->  prd.md  --(propose)-->  openspec/changes/<id>/
                                                            --(apply)-->  impl/

Stage ``prd``   the PRD is ready to become an OpenSpec change: every
                requirement has an ID, uses SHALL/MUST, carries a WHEN/THEN,
                avoids the ticket's vague words, and pins down every fact the
                stakeholder gave.
Stage ``spec``  the OpenSpec change is valid (the rules ``openspec validate
                --strict`` enforces that matter here) and traces to the PRD in
                both directions -- nothing dropped, nothing invented.
Stage ``build`` every scenario is named by a test, every test names a real
                scenario, every task is ticked, the tests pass, and the
                exercise's own implementation rules hold.

The report uses the same shape as the ai-literacy-superpowers
``harness-enforcer`` agent, because this script *is* the Tool line of the
deterministic constraints in each exercise's HARNESS.md. The agent-backed
constraints ("Spec captures intent", "No gold-plating") need a model and are
not judged here.

Stdlib only, offline: the grading must run in CI with no Docker daemon, no
LangChain install, and no MCP client.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

STAGES = ("prd", "spec", "build")

# From OpenSpec's src/core/validation/constants.ts. Copied, not imported: the
# point is to run without Node. If upstream moves these, the lesson text that
# quotes them has to move too.
MIN_WHY = 50
MAX_WHY = 1000
DELTA_HEADERS = ("ADDED", "MODIFIED", "REMOVED", "RENAMED")

PRD_ID = re.compile(r"\bPRD-(\d+)\b")
PRD_HEADING = re.compile(r"^###\s+(PRD-\d+)\b[:.\s-]*(.*)$")
SHALL = re.compile(r"\b(SHALL|MUST)\b")
SCENARIO_TAG = re.compile(r"Scenario:\s*(.+?)\s*$")


@dataclass
class Finding:
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.where} -- {self.message}"


@dataclass
class StageResult:
    name: str
    title: str
    findings: list[Finding] = field(default_factory=list)
    skipped: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.skipped and not self.findings

    def add(self, where: str, message: str) -> None:
        self.findings.append(Finding(where, message))


@dataclass
class Requirement:
    name: str
    section: str
    body: str
    scenarios: dict[str, str]
    line: int


# --------------------------------------------------------------------------
# Locating things


def find_rubric(target: Path) -> tuple[Path, dict]:
    """The rubric lives next to ticket.md. A ``solution/`` folder borrows its
    parent's, which is what lets a learner judge the reference answer with the
    same command they judge their own with."""
    for directory in (target, target.parent):
        candidate = directory / "rubric.json"
        if candidate.is_file():
            return directory, json.loads(candidate.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"no rubric.json in {target} or its parent")


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def find_change(answer: Path) -> tuple[Path | None, str]:
    changes = answer / "openspec" / "changes"
    if not changes.is_dir():
        return None, f"no {rel(changes, answer)}/ -- run /opsx:propose, or create it by hand"
    live = sorted(
        d for d in changes.iterdir() if d.is_dir() and d.name != "archive" and not d.name.startswith(".")
    )
    if len(live) != 1:
        names = ", ".join(d.name for d in live) or "none"
        return None, f"expected exactly one active change under openspec/changes/, found: {names}"
    return live[0], ""


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


# --------------------------------------------------------------------------
# Parsing


def sections(text: str, level: int = 2) -> dict[str, str]:
    """Split markdown on headings of exactly ``level``, fences respected."""
    marker = "#" * level + " "
    out: dict[str, list[str]] = {}
    current: str | None = None
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith(marker):
            current = line[len(marker):].strip()
            out.setdefault(current, [])
            continue
        if current is not None:
            out[current].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def section_named(text: str, *names: str, level: int = 2) -> str | None:
    wanted = {n.lower() for n in names}
    for heading, body in sections(text, level).items():
        if heading.lower() in wanted:
            return body
    return None


def prd_requirements(text: str) -> dict[str, tuple[str, str]]:
    """``### PRD-n: title`` blocks inside ``## Requirements`` -> (title, body)."""
    body = section_named(text, "Requirements") or ""
    found: dict[str, tuple[str, list[str]]] = {}
    current: str | None = None
    for line in body.splitlines():
        m = PRD_HEADING.match(line)
        if m:
            current = m.group(1)
            found[current] = (m.group(2).strip(), [])
            continue
        if line.startswith("### "):
            current = None
            continue
        if current:
            found[current][1].append(line)
    return {k: (title, "\n".join(lines).strip()) for k, (title, lines) in found.items()}


def spec_requirements(text: str) -> tuple[list[Requirement], list[str]]:
    """Requirements inside delta sections, plus the names of any stranded
    outside one (OpenSpec silently ignores those, so we do not)."""
    reqs: list[Requirement] = []
    orphans: list[str] = []
    section = ""
    current: Requirement | None = None
    scenario: str | None = None
    in_fence = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if in_fence:
            if current is not None:
                _append(current, scenario, line)
            continue
        if line.startswith("## "):
            head = line[3:].strip()
            section = head.split()[0].upper() if head.upper().endswith("REQUIREMENTS") else ""
            current, scenario = None, None
            continue
        if line.startswith("### Requirement:"):
            name = line.split(":", 1)[1].strip()
            if section not in DELTA_HEADERS:
                orphans.append(name)
                current = None
                continue
            current = Requirement(name, section, "", {}, number)
            reqs.append(current)
            scenario = None
            continue
        if line.startswith("### "):
            current, scenario = None, None
            continue
        if current is None:
            continue
        if line.startswith("#### Scenario:"):
            scenario = line.split(":", 1)[1].strip()
            current.scenarios[scenario] = ""
            continue
        _append(current, scenario, line)
    for r in reqs:
        r.body = r.body.strip()
        r.scenarios = {k: v.strip() for k, v in r.scenarios.items()}
    return reqs, orphans


def _append(req: Requirement, scenario: str | None, line: str) -> None:
    if scenario is None:
        req.body += line + "\n"
    else:
        req.scenarios[scenario] += line + "\n"


def tasks(text: str) -> list[tuple[bool, str]]:
    out = []
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]\s+\[([ xX])\]\s+(.*)$", line)
        if m:
            out.append((m.group(1).lower() == "x", m.group(2).strip()))
    return out


def test_scenario_tags(tests_dir: Path) -> dict[str, list[str]]:
    """Map scenario name -> test files naming it with ``Scenario: <name>``."""
    tags: dict[str, list[str]] = {}
    for py in sorted(tests_dir.rglob("test_*.py")):
        for line in read(py).splitlines():
            m = SCENARIO_TAG.search(line)
            if m:
                name = m.group(1).strip().strip("\"'").rstrip(".")
                tags.setdefault(name, []).append(py.name)
    return tags


def strip_code(text: str) -> str:
    kept, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            kept.append(re.sub(r"`[^`]*`", "", line))
    return "\n".join(kept)


# --------------------------------------------------------------------------
# Stages


def judge_prd(answer: Path, rubric: dict) -> StageResult:
    res = StageResult("prd", TITLES["prd"])
    path = answer / "prd.md"
    if not path.is_file():
        res.add("prd.md", "missing -- turn ticket.md into a PRD first (lesson 3, steps 1-2)")
        return res
    text = read(path)

    for name in ("Problem", "Requirements", "Non-goals", "Open questions"):
        if section_named(text, name) is None:
            res.add("prd.md", f"no '## {name}' section")

    reqs = prd_requirements(text)
    if not reqs:
        res.add("prd.md", "no '### PRD-<n>: <title>' requirements under '## Requirements'")
        return res

    vague = [re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE) for w in rubric["vague_terms"]]
    for rid, (title, body) in reqs.items():
        where = f"prd.md {rid}"
        if not body:
            res.add(where, "empty requirement")
            continue
        if not SHALL.search(body):
            res.add(where, "no SHALL or MUST -- OpenSpec rejects a requirement without one")
        prose = strip_code(body)
        if not (re.search(r"\bWHEN\b", prose) and re.search(r"\bTHEN\b", prose)):
            res.add(where, "no WHEN/THEN acceptance -- it will not become a #### Scenario")
        for pattern in vague:
            hit = pattern.search(strip_code(title + "\n" + body))
            if hit:
                res.add(where, f"vague term '{hit.group(0)}' -- replace it with the number or behaviour it stands for")

    open_q = section_named(text, "Open questions") or ""
    for line in open_q.splitlines():
        if re.search(r"\bTBD\b|\bTODO\b|\?\?\?", line):
            res.add("prd.md Open questions", f"unresolved: {line.strip()}")

    requirements_text = "\n".join(body for _, body in reqs.values())
    for fact in rubric["prd_facts"]:
        if not any(re.search(p, requirements_text, re.IGNORECASE) for p in fact["any_of"]):
            res.add("prd.md", f"does not pin down {fact['label']} ({fact['source']})")
    return res


def judge_spec(answer: Path, rubric: dict) -> StageResult:
    res = StageResult("spec", TITLES["spec"])
    change, why = find_change(answer)
    if change is None:
        res.add("openspec/", why)
        return res
    where = rel(change, answer)

    proposal = change / "proposal.md"
    if not proposal.is_file():
        res.add(where, "no proposal.md")
    else:
        text = read(proposal)
        why_body = section_named(text, "Why")
        if why_body is None:
            res.add(f"{where}/proposal.md", "no '## Why' section")
        elif not MIN_WHY <= len(why_body) <= MAX_WHY:
            res.add(f"{where}/proposal.md", f"'## Why' is {len(why_body)} chars; OpenSpec wants {MIN_WHY}-{MAX_WHY}")
        if not section_named(text, "What Changes"):
            res.add(f"{where}/proposal.md", "no (or empty) '## What Changes' section")

    task_file = change / "tasks.md"
    if not task_file.is_file() or not tasks(read(task_file)):
        res.add(f"{where}/tasks.md", "missing, or has no '- [ ]' checkbox tasks")

    spec_files = sorted((change / "specs").glob("*/spec.md")) if (change / "specs").is_dir() else []
    if not spec_files:
        res.add(where, "no specs/<capability>/spec.md delta")
        return res

    prd_ids = set(prd_requirements(read(answer / "prd.md"))) if (answer / "prd.md").is_file() else set()
    traced: set[str] = set()
    seen: set[str] = set()
    for spec in spec_files:
        sw = rel(spec, answer)
        reqs, orphans = spec_requirements(read(spec))
        for name in orphans:
            res.add(sw, f"Requirement '{name}' is outside a delta section; OpenSpec ignores it")
        if not reqs:
            res.add(sw, "no requirements under '## ADDED/MODIFIED Requirements'")
        for r in reqs:
            rw = f"{sw}:{r.line} '{r.name}'"
            if r.name in seen:
                res.add(rw, "duplicate requirement name")
            seen.add(r.name)
            if r.section == "REMOVED":
                continue
            if not SHALL.search(r.body):
                hint = " (it is only in the header -- move it into the body)" if SHALL.search(r.name) else ""
                res.add(rw, f"body has no SHALL or MUST{hint}")
            if not r.scenarios:
                res.add(rw, "no '#### Scenario:' -- every requirement needs one")
            for sname, sbody in r.scenarios.items():
                if not sbody:
                    res.add(rw, f"scenario '{sname}' is empty")
                elif not (re.search(r"\bWHEN\b", sbody) and re.search(r"\bTHEN\b", sbody)):
                    res.add(rw, f"scenario '{sname}' needs WHEN and THEN")
            ids = set(PRD_ID.findall(r.body))
            refs = {f"PRD-{n}" for n in ids}
            if not refs:
                res.add(rw, "traces to no PRD requirement -- add 'Trace: PRD-<n>' or cut it (gold-plating)")
            for ref in sorted(refs - prd_ids):
                res.add(rw, f"traces to {ref}, which the PRD does not define")
            traced |= refs & prd_ids

    for rid in sorted(prd_ids - traced, key=lambda s: int(s.split("-")[1])):
        res.add("prd.md", f"{rid} is not traced by any spec requirement -- it was dropped")
    return res


def judge_build(answer: Path, rubric: dict, run_tests: bool = True) -> StageResult:
    res = StageResult("build", TITLES["build"])
    change, why = find_change(answer)
    impl = answer / "impl"
    if change is None:
        res.add("openspec/", why)
        return res
    if not impl.is_dir():
        res.add("impl/", "missing -- build against the spec (lesson 3, step 4)")
        return res

    scenarios: dict[str, str] = {}
    for spec in sorted((change / "specs").glob("*/spec.md")):
        for r in spec_requirements(read(spec))[0]:
            if r.section != "REMOVED":
                for s in r.scenarios:
                    scenarios[s] = r.name

    tests_dir = impl / "tests"
    tags = test_scenario_tags(tests_dir) if tests_dir.is_dir() else {}
    for s, req in scenarios.items():
        if s not in tags:
            res.add("impl/tests", f"no test names 'Scenario: {s}' (requirement '{req}')")
    for s, files in tags.items():
        if s not in scenarios:
            res.add(f"impl/tests/{files[0]}", f"names 'Scenario: {s}', which the spec does not contain -- stale or invented")

    task_file = change / "tasks.md"
    if task_file.is_file():
        for done, text in tasks(read(task_file)):
            if not done:
                res.add(rel(task_file, answer), f"unticked: {text}")

    for rule in rubric.get("impl_rules", []):
        files = sorted(impl.glob(rule["glob"]))
        if not files:
            res.add("impl/", f"no file matches {rule['glob']} ({rule['label']})")
            continue
        blob = "\n".join(read(f) for f in files)
        for pattern in rule.get("must_match", []):
            if not re.search(pattern, blob, re.MULTILINE):
                res.add(f"impl/{rule['glob']}", f"{rule['label']}: expected /{pattern}/")
        for pattern in rule.get("must_not_match", []):
            m = re.search(pattern, blob, re.MULTILINE)
            if m:
                res.add(f"impl/{rule['glob']}", f"{rule['label']}: found '{m.group(0)}'")

    if run_tests and tests_dir.is_dir() and not res.findings:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
            cwd=str(impl),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout).strip().splitlines()[-12:]
            res.add("impl/tests", "tests fail:\n    " + "\n    ".join(tail))
        else:
            # A skipped scenario test is not a failed one, but a green run
            # that quietly skipped half the scenarios is not the whole story
            # either -- so say how many, every time.
            m = re.search(r"skipped=(\d+)", proc.stderr)
            if m:
                res.notes.append(
                    f"{m.group(1)} test(s) skipped -- their scenarios are tagged but were not "
                    "exercised here; install the optional dependency to run them"
                )
    return res


JUDGES = {"prd": judge_prd, "spec": judge_spec, "build": judge_build}
TITLES = {
    "prd": "PRD is OpenSpec-ready",
    "spec": "OpenSpec change is valid and traces to the PRD",
    "build": "Implementation is faithful to the spec",
}


def judge(target: Path, stages: tuple[str, ...] = STAGES, run_tests: bool = True) -> list[StageResult]:
    """Judge stages in order; a later stage is skipped once an earlier fails.

    Skipping is deliberate. A spec judged against a broken PRD produces a
    wall of findings that are all the same root cause, and a wall of
    findings is the thing people learn to scroll past.
    """
    _, rubric = find_rubric(target)
    results: list[StageResult] = []
    blocked = ""
    for name in STAGES:
        if name not in stages:
            continue
        if blocked:
            results.append(StageResult(name, TITLES[name], skipped=f"blocked by {blocked}"))
            continue
        if name == "build":
            r = judge_build(target, rubric, run_tests=run_tests)
        else:
            r = JUDGES[name](target, rubric)
        results.append(r)
        if not r.ok:
            blocked = name
    return results


HINTS = {
    "prd": "interrogate ticket.md (answers are in stakeholder-answers.md) and write prd.md -- lesson 3, steps 1-2",
    "spec": "turn prd.md into openspec/changes/<id>/ with /opsx:propose or by hand -- lesson 3, step 3",
    "build": "build impl/ test-first, one test per '#### Scenario:' -- lesson 3, step 4",
}


def grade(answer: Path) -> tuple[bool, str, str]:
    """``(ok, message, hint)`` for tutorials/check.py.

    Returns plain values rather than an ``exercise_api.Result`` so this file
    stays runnable on its own, outside the tutorial runner.
    """
    results = judge(answer)
    if all(r.ok for r in results):
        notes = "".join(f" ({n})" for r in results for n in r.notes)
        return True, f"prd, spec and build all faithful{notes} -- now run the agent-backed half (lesson 3, step 5)", ""
    failed = next(r for r in results if not r.ok and not r.skipped)
    shown = "; ".join(str(f) for f in failed.findings[:3])
    more = len(failed.findings) - 3
    suffix = f" (+{more} more)" if more > 0 else ""
    shown_path = rel(answer, Path(__file__).resolve().parents[2])
    command = f"python tutorials/50-spec-fidelity/spec_fidelity.py {shown_path}"
    return False, f"[{failed.name}] {shown}{suffix}", f"{HINTS[failed.name]}; full report: {command}"


def report(results: list[StageResult]) -> str:
    lines = ["## Constraint Results", ""]
    for r in results:
        status = "PASS" if r.ok else ("UNCHECKED" if r.skipped else "FAIL")
        lines.append(f"### {r.title} — {status}")
        lines.append("Enforcement: deterministic")
        lines.append(f"Tool: spec_fidelity.py --stage {r.name}")
        if r.skipped:
            lines.append(f"Skipped: {r.skipped}")
        lines.extend(f"Note: {n}" for n in r.notes)
        if r.findings:
            lines.append("Findings:")
            lines.extend(f"- {f}" for f in r.findings)
        lines.append("")
    passed = sum(r.ok for r in results)
    failed = sum(1 for r in results if not r.ok and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)
    lines += ["---", f"Summary: {passed} passed, {failed} failed, {skipped} unchecked"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", type=Path, help="an exercise folder, or its solution/ folder")
    parser.add_argument("--stage", choices=(*STAGES, "all"), default="all")
    parser.add_argument("--no-tests", action="store_true", help="skip running impl/tests")
    # Claude Code aborts a slash command whose `!` shell line exits non-zero,
    # so a command that runs the judge in order to explain its failures would
    # never see them. Same escape hatch linters use.
    parser.add_argument("--exit-zero", action="store_true", help="exit 0 even when a stage fails")
    args = parser.parse_args(argv)
    stages = STAGES if args.stage == "all" else (args.stage,)
    results = judge(args.target.resolve(), stages, run_tests=not args.no_tests)
    sys.stdout.reconfigure(encoding="utf-8")
    print(report(results))
    return 0 if args.exit_zero or all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
