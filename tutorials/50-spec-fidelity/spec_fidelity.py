"""The deterministic half of the fidelity judge for track 50.

    python tutorials/50-spec-fidelity/spec_fidelity.py <exercise-dir>
    python tutorials/50-spec-fidelity/spec_fidelity.py <exercise-dir> --stage prd
    python tutorials/50-spec-fidelity/spec_fidelity.py <exercise-dir>/solution

It judges three artifacts against each other, in the order they are written:

    ticket.md  --(interrogate)-->  prd.md  --(propose)-->  openspec/changes/<id>/
                                                            --(apply)-->  impl/

Stage ``prd``   the PRD is ready to become an OpenSpec change: every
                requirement has an ID, uses SHALL/MUST, carries a WHEN/THEN,
                avoids the ticket's vague words, pins down every fact the
                stakeholder gave, and contradicts none of them.
Stage ``spec``  the OpenSpec change is valid (the rules ``openspec validate
                --strict`` enforces that matter here, plus a few it does not)
                and traces to the PRD in both directions -- nothing dropped,
                nothing invented.
Stage ``build`` every scenario is named by a unittest test that runs, asserts
                something and passes; every test names a real scenario; every
                task is ticked; the exercise's own implementation rules hold.

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
import ast
import io
import json
import re
import subprocess
import sys
import tempfile
import tokenize
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

TRACK = Path(__file__).resolve().parent
STAGES = ("prd", "spec", "build")
MARKER = ".fidelity.json"

# From OpenSpec's src/core/validation/constants.ts. Copied, not imported: the
# point is to run without Node. If upstream moves these, the lesson text that
# quotes them has to move too.
MIN_WHY = 50
MAX_WHY = 1000
DELTA_HEADERS = ("ADDED", "MODIFIED", "REMOVED", "RENAMED")

PRD_ID = re.compile(r"\bPRD-0*(\d+)\b")
PRD_HEADING = re.compile(r"^#{3,4}\s+PRD-0*(\d+)\b[\s:.\-–—]*(.*)$")
TRACE_LINE = re.compile(r"^\s*(?:[-*]\s*)?\**Trace\**:\s*(.+)$", re.MULTILINE)
SHALL = re.compile(r"\b(SHALL|MUST)\b")
TEST_TIMEOUT = 300

# Heading aliases a reasonable PRD uses. Rejecting "## Out of Scope" for not
# being spelled "## Non-goals" is a checker crying wolf.
PRD_SECTIONS = {
    "Problem": ("problem", "problem statement", "background"),
    "Requirements": ("requirements", "functional requirements"),
    "Non-goals": ("non-goals", "non goals", "nongoals", "out of scope"),
    "Open questions": ("open questions", "questions", "resolved questions"),
}


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
    capability: str
    section: str
    body: str
    scenarios: dict[str, str]
    traces: set[str]
    line: int


# --------------------------------------------------------------------------
# Locating things


def find_rubric(target: Path) -> tuple[Path, dict]:
    """Find the rubric without putting it in front of the developer.

    In the repo it sits next to ticket.md, and a ``solution/`` folder borrows
    its parent's. A workspace made by start.py holds only a marker naming the
    exercise: the rubric's facts *are* the stakeholder's answers, so copying
    it into a folder Claude reads would hand them over.
    """
    for directory in (target, target.parent):
        candidate = directory / "rubric.json"
        if candidate.is_file():
            return directory, json.loads(read(candidate))
    marker = target / MARKER
    if marker.is_file():
        exercise = json.loads(read(marker))["exercise"]
        candidate = TRACK / "exercises" / exercise / "rubric.json"
        return candidate.parent, json.loads(read(candidate))
    raise FileNotFoundError(f"no rubric.json or {MARKER} in {target} or its parent")


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def find_change(answer: Path) -> tuple[Path | None, str]:
    changes = answer / "openspec" / "changes"
    if not changes.is_dir():
        return None, f"no {rel(changes, answer)}/ -- run /fidelity:propose, or create it by hand"
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


def canon(ident: str) -> str:
    m = PRD_ID.search(ident)
    return f"PRD-{int(m.group(1))}" if m else ident


# --------------------------------------------------------------------------
# Parsing markdown


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
        if heading.lower().strip(" :") in wanted:
            return body
    return None


def prd_section(text: str, canonical: str) -> str | None:
    return section_named(text, canonical, *PRD_SECTIONS[canonical])


def prd_requirements(text: str) -> dict[str, tuple[str, str]]:
    """``### PRD-n: title`` blocks (or ``####`` under a group heading) inside
    the requirements section -> {canonical id: (title, body)}."""
    body = prd_section(text, "Requirements") or ""
    found: dict[str, tuple[str, list[str]]] = {}
    current: str | None = None
    for line in body.splitlines():
        m = PRD_HEADING.match(line)
        if m:
            current = f"PRD-{int(m.group(1))}"
            found[current] = (m.group(2).strip(), [])
            continue
        if line.startswith("### ") or line.startswith("#### "):
            current = None
            continue
        if current:
            found[current][1].append(line)
    return {k: (title, "\n".join(lines).strip()) for k, (title, lines) in found.items()}


def flatten(text: str) -> str:
    """One line per paragraph or bullet.

    Fact patterns use ``[^\\n]*`` to mean "in the same sentence". Without
    this, a PRD hard-wrapped at 80 columns -- this repo's own style -- fails a
    fact because the status code and the error name landed on adjacent lines.
    """
    units: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        starts_unit = (
            not stripped
            or not units
            or re.match(r"^([-*+]|\d+[.)])\s", stripped)
            or stripped.startswith("#")
            or not units[-1]
        )
        if starts_unit:
            units.append(stripped)
        else:
            units[-1] += " " + stripped
    return "\n".join(u for u in units if u)


def spec_requirements(text: str, capability: str = "") -> tuple[list[Requirement], list[str]]:
    """Requirements inside delta sections, plus the names of any stranded
    outside one (OpenSpec reports those; so do we)."""
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
            current = Requirement(name, capability, section, "", {}, set(), number)
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
        # A Trace line counts wherever it sits in the requirement's block --
        # "end every requirement with a Trace line" puts it after the scenarios.
        block = r.body + "\n" + "\n".join(r.scenarios.values())
        for m in TRACE_LINE.finditer(block):
            r.traces |= {canon(i) for i in re.findall(r"PRD-0*\d+", m.group(1))}
        r.body = TRACE_LINE.sub("", r.body).strip()
        r.scenarios = {k: TRACE_LINE.sub("", v).strip() for k, v in r.scenarios.items()}
    return reqs, orphans


def _append(req: Requirement, scenario: str | None, line: str) -> None:
    if scenario is None:
        req.body += line + "\n"
    else:
        req.scenarios[scenario] += line + "\n"


def change_requirements(change: Path) -> list[Requirement]:
    out: list[Requirement] = []
    for spec in sorted((change / "specs").glob("**/spec.md")):
        capability = spec.parent.relative_to(change / "specs").as_posix()
        out.extend(spec_requirements(read(spec), capability)[0])
    return out


def tasks(text: str) -> list[tuple[bool, str]]:
    out = []
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]\s+\[([ xX])\]\s+(.*)$", line)
        if m:
            out.append((m.group(1).lower() == "x", m.group(2).strip()))
    return out


def strip_code(text: str) -> str:
    """Drop fenced blocks, inline code and quoted speech.

    A vague word inside `code`, a path, or a customer's quoted question is
    not the PRD being vague -- flagging it is the checker crying wolf.
    """
    kept, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            line = re.sub(r"`[^`]*`", "", line)
            line = re.sub(r"\"[^\"]*\"|“[^”]*”", "", line)
            kept.append(line)
    return "\n".join(kept)


# --------------------------------------------------------------------------
# Parsing code


def strip_py(source: str) -> str:
    """Python with comments and docstrings blanked out.

    ``# never use shell=True`` is the opposite of using it. A rule that
    fires on the comment teaches people to stop writing the comment.
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError):
        return source
    lines = source.splitlines(keepends=True)
    drop: list[tuple[tuple[int, int], tuple[int, int]]] = []
    prev = tokenize.NEWLINE
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            drop.append((tok.start, tok.end))
        elif tok.type == tokenize.STRING and prev in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT):
            drop.append((tok.start, tok.end))
        if tok.type not in (tokenize.COMMENT, tokenize.NL):
            prev = tok.type
    for (sr, sc), (er, ec) in reversed(drop):
        if sr == er:
            line = lines[sr - 1]
            lines[sr - 1] = line[:sc] + " " * (ec - sc) + line[ec:]
        else:
            lines[sr - 1] = lines[sr - 1][:sc] + "\n"
            for i in range(sr, er - 1):
                lines[i] = "\n"
            lines[er - 1] = " " * ec + lines[er - 1][ec:]
    return "".join(lines)


def strip_dockerfile(source: str) -> str:
    """Comments gone, ``\\`` continuations joined: one instruction per line,
    so a rule about RUN sees the whole RUN."""
    joined = re.sub(r"\\\n", " ", source)
    return "\n".join(l for l in joined.splitlines() if not l.lstrip().startswith("#"))


def prepared(path: Path) -> str:
    text = read(path)
    if path.suffix == ".py":
        return strip_py(text)
    if path.name.startswith("Dockerfile") or path.suffix == ".dockerfile":
        return strip_dockerfile(text)
    return text


@dataclass
class TaggedTest:
    file: str
    owner: str  # class name, or "" for a module-level function
    name: str
    scenario: str
    asserts: bool


def _asserts(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Assert):
            return True
        if isinstance(sub, ast.Call):
            f = sub.func
            name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
            if name.startswith(("assert", "fail")):
                return True
    return False


def _scenario_of(doc: str | None) -> str | None:
    first = (doc or "").strip().splitlines()[0].strip() if (doc or "").strip() else ""
    if not first.startswith("Scenario:"):
        return None
    return first[len("Scenario:"):].strip().strip("\"'").rstrip(".")


def tagged_tests(tests_dir: Path) -> list[TaggedTest]:
    """Tests whose docstring's first line is ``Scenario: <name>``.

    Only a docstring counts. A tag in a comment is a promise, not a test.
    """
    found: list[TaggedTest] = []
    for py in sorted(tests_dir.rglob("test_*.py")):
        try:
            tree = ast.parse(read(py))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                s = _scenario_of(ast.get_docstring(node))
                if s:
                    found.append(TaggedTest(py.name, "", node.name, s, _asserts(node)))
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test"):
                        s = _scenario_of(ast.get_docstring(item))
                        if s:
                            found.append(TaggedTest(py.name, node.name, item.name, s, _asserts(item)))
    return found


# Runs in the implementation's own interpreter and folder, and reports every
# test's outcome with its scenario -- so "tagged" can mean "ran and passed",
# not "the string appears in a file".
RUNNER = r'''
import json, sys, unittest
sys.path.insert(0, ".")
records = []

def scenario(test):
    method = getattr(test, getattr(test, "_testMethodName", ""), None)
    doc = (getattr(method, "__doc__", None) or "").strip()
    first = doc.splitlines()[0].strip() if doc else ""
    return first[9:].strip().strip("\"'").rstrip(".") if first.startswith("Scenario:") else None

class Result(unittest.TestResult):
    def rec(self, test, outcome, detail=""):
        records.append({"id": test.id(), "outcome": outcome, "detail": detail[-1500:], "scenario": scenario(test)})
    def addSuccess(self, test):
        self.rec(test, "pass")
    def addFailure(self, test, err):
        self.rec(test, "fail", self._exc_info_to_string(err, test))
    def addError(self, test, err):
        self.rec(test, "error", self._exc_info_to_string(err, test))
    def addSkip(self, test, reason):
        self.rec(test, "skip", reason)
    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.rec(test, "fail", self._exc_info_to_string(err, test))
    def addExpectedFailure(self, test, err):
        self.rec(test, "fail", "marked expectedFailure")
    def addUnexpectedSuccess(self, test):
        self.rec(test, "fail", "unexpected success")

unittest.defaultTestLoader.discover("tests", top_level_dir=".").run(Result())
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(records, fh)
'''


def run_tests(impl: Path) -> tuple[list[dict] | None, str]:
    with tempfile.TemporaryDirectory(prefix="fidelity-") as tmp:
        out = Path(tmp) / "results.json"
        try:
            proc = subprocess.run(
                [sys.executable, "-c", RUNNER, str(out)],
                cwd=str(impl), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=TEST_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return None, f"tests did not finish within {TEST_TIMEOUT} s"
        if not out.is_file():
            tail = "\n    ".join((proc.stderr or proc.stdout).strip().splitlines()[-8:])
            return None, f"the test run crashed before reporting:\n    {tail}"
        return json.loads(out.read_text(encoding="utf-8")), ""


def _last_line(detail: str) -> str:
    """The exception line of a traceback -- not the last line, which for an
    assertEqual on strings is a difflib marker like ``?    ^``."""
    lines = [l.strip() for l in detail.strip().splitlines() if l.strip()]
    errors = [l for l in lines if re.match(r"^[\w.]+(Error|Exception|Exit|Interrupt)\b", l)]
    return (errors or lines or ["no detail"])[-1]


# --------------------------------------------------------------------------
# Stages


def judge_prd(answer: Path, rubric: dict) -> StageResult:
    res = StageResult("prd", TITLES["prd"])
    path = answer / "prd.md"
    if not path.is_file():
        res.add("prd.md", "missing -- interrogate the ticket, then write the PRD (lesson 3, steps 1-2)")
        return res
    text = read(path)

    for canonical in PRD_SECTIONS:
        if prd_section(text, canonical) is None:
            res.add("prd.md", f"no '## {canonical}' section")

    reqs = prd_requirements(text)
    if not reqs:
        found = [h for h in sections(text) if h]
        res.add("prd.md", "no '### PRD-<n>: <title>' requirements under '## Requirements' "
                          f"(top-level headings found: {', '.join(found) or 'none'})")
        return res

    vague = [
        re.compile(rf"(?<![\w/.-]){re.escape(w)}(?![\w/])", re.IGNORECASE) for w in rubric["vague_terms"]
    ]
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

    open_q = prd_section(text, "Open questions") or ""
    for line in open_q.splitlines():
        if re.search(r"\bTBD\b|\bTODO\b|\?\?\?", line):
            res.add("prd.md Open questions", f"unresolved: {line.strip()}")

    stated = flatten("\n\n".join(body for _, body in reqs.values()))
    for fact in rubric["prd_facts"]:
        verdict = fact_verdict(fact, stated)
        source = fact["source"].replace("stakeholder-answers.md", "PO notes")
        if verdict == "missing":
            res.add("prd.md", f"does not pin down {fact['label']} -- ask the product owner ({source})")
        elif verdict.startswith("contradicts:"):
            res.add("prd.md", f"contradicts the product owner on {fact['label']}: "
                              f"'{verdict.split(':', 1)[1]}' ({source})")
    return res


def fact_verdict(fact: dict, text: str) -> str:
    """"ok", "missing", or "contradicts:<the offending words>".

    ``any_of`` proves the fact was mentioned; ``none_of`` catches it being
    mentioned the wrong way round -- "SHALL set temperature to 0.7" mentions
    temperature too.
    """
    for pattern in fact.get("none_of", []):
        for m in re.finditer(pattern, text, re.IGNORECASE):
            if not _negated(text, m.start()):
                return "contradicts:" + m.group(0)
    if any(re.search(p, text, re.IGNORECASE) for p in fact["any_of"]):
        return "ok"
    return "missing"


NEGATION = re.compile(r"\b(not|never|no|none|without|instead of|rather than)\b", re.IGNORECASE)


def _negated(text: str, start: int) -> bool:
    """Whether the clause leading up to ``start`` already negates it.

    "no money values appear as JSON floats" is the fact stated correctly,
    not contradicted. Found the hard way: Haiku wrote exactly that line and
    the first version of this check called it a contradiction.
    """
    clause_start = max(text.rfind(c, 0, start) for c in ".;!?\n") + 1
    return bool(NEGATION.search(text[clause_start:start]))


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
            res.add(f"{where}/proposal.md", f"'## Why' is {len(why_body)} chars; OpenSpec's guidance is {MIN_WHY}-{MAX_WHY}")
        if not section_named(text, "What Changes"):
            res.add(f"{where}/proposal.md", "no (or empty) '## What Changes' section")

    task_file = change / "tasks.md"
    if not task_file.is_file() or not tasks(read(task_file)):
        res.add(f"{where}/tasks.md", "missing, or has no '- [ ]' checkbox tasks")

    spec_files = sorted((change / "specs").glob("**/spec.md")) if (change / "specs").is_dir() else []
    if not spec_files:
        res.add(where, "no specs/<capability>/spec.md delta")
        return res

    prd_ids = set(prd_requirements(read(answer / "prd.md"))) if (answer / "prd.md").is_file() else set()
    traced_by: dict[str, list[Requirement]] = defaultdict(list)
    seen_req: set[tuple[str, str]] = set()
    seen_scenario: dict[str, str] = {}
    for spec in spec_files:
        sw = rel(spec, answer)
        capability = spec.parent.relative_to(change / "specs").as_posix()
        reqs, orphans = spec_requirements(read(spec), capability)
        for name in orphans:
            res.add(sw, f"Requirement '{name}' is outside a delta section; OpenSpec ignores it")
        if not reqs:
            res.add(sw, "no requirements under '## ADDED/MODIFIED Requirements'")
        for r in reqs:
            rw = f"{sw}:{r.line} '{r.name}'"
            # Keyed on capability too: OpenSpec accepts the same requirement
            # name in two capabilities, and so must we.
            if (r.capability, r.name) in seen_req:
                res.add(rw, "duplicate requirement name in this capability")
            seen_req.add((r.capability, r.name))
            if r.section == "REMOVED":
                continue
            if not SHALL.search(r.body):
                hint = " (it is only in the header -- move it into the body)" if SHALL.search(r.name) else ""
                res.add(rw, f"body has no SHALL or MUST{hint}")
            if not r.scenarios:
                res.add(rw, "no '#### Scenario:' -- every requirement needs one")
            for sname, sbody in r.scenarios.items():
                if sname in seen_scenario:
                    res.add(rw, f"scenario name '{sname}' is also used by '{seen_scenario[sname]}' -- "
                                "tests cite scenarios by name, so names must be unique")
                seen_scenario[sname] = r.name
                if not sbody:
                    res.add(rw, f"scenario '{sname}' is empty")
                elif not (re.search(r"\bWHEN\b", sbody) and re.search(r"\bTHEN\b", sbody)):
                    res.add(rw, f"scenario '{sname}' needs WHEN and THEN")
            if not r.traces:
                res.add(rw, "no 'Trace: PRD-<n>' line -- trace it to the PRD, or cut it (gold-plating)")
            for ref in sorted(r.traces - prd_ids):
                res.add(rw, f"traces to {ref}, which the PRD does not define")
            for ref in r.traces & prd_ids:
                traced_by[ref].append(r)

    for rid in sorted(prd_ids, key=lambda s: int(s.split("-")[1])):
        reqs_for = traced_by.get(rid, [])
        if not reqs_for:
            res.add("prd.md", f"{rid} is not traced by any spec requirement -- it was dropped")
        elif all(len(r.traces) > 1 for r in reqs_for):
            # Adding PRD-7 to another requirement's Trace line is the quiet way
            # to drop PRD-7. Give every PRD item one requirement of its own.
            names = ", ".join(f"'{r.name}'" for r in reqs_for)
            res.add("prd.md", f"{rid} is only traced alongside other PRD ids (by {names}) -- "
                              "give it a requirement of its own, so dropping it cannot hide")
    return res


def judge_build(answer: Path, rubric: dict, run: bool = True, allow_skips: bool = False) -> StageResult:
    res = StageResult("build", TITLES["build"])
    change, why = find_change(answer)
    impl = answer / "impl"
    if change is None:
        res.add("openspec/", why)
        return res
    if not impl.is_dir():
        res.add("impl/", "missing -- build against the spec (lesson 3, step 4)")
        return res

    scenarios = {s: r.name for r in change_requirements(change) if r.section != "REMOVED" for s in r.scenarios}

    # Layout first, one finding each: a missing __init__.py otherwise shows
    # up as twelve lines of unittest internals, or as one finding per scenario.
    tests_dir = impl / "tests"
    layout_ok = True
    if not tests_dir.is_dir():
        res.add("impl/", "no tests/ folder -- tests live in impl/tests/test_*.py")
        layout_ok = False
    else:
        if not (tests_dir / "__init__.py").is_file():
            res.add("impl/tests", "no __init__.py -- unittest discovery needs tests/ to be a package (an empty file is enough)")
            layout_ok = False
        if not any(tests_dir.rglob("test_*.py")):
            others = sorted(p.name for p in tests_dir.rglob("*.py") if p.name != "__init__.py")
            hint = f" (found {', '.join(others)})" if others else ""
            res.add("impl/tests", f"no test_*.py files{hint} -- unittest discovers test_*.py only")
            layout_ok = False

    if layout_ok:
        tagged = tagged_tests(tests_dir)
        by_scenario: dict[str, list[TaggedTest]] = defaultdict(list)
        for t in tagged:
            by_scenario[t.scenario].append(t)
        for t in tagged:
            where = f"impl/tests/{t.file}"
            if not t.owner:
                res.add(where, f"'{t.name}' is a module-level function -- unittest does not collect it; "
                               "make it a method of a unittest.TestCase class")
            elif not t.asserts:
                res.add(where, f"{t.owner}.{t.name} names 'Scenario: {t.scenario}' but asserts nothing")
            if t.scenario not in scenarios:
                res.add(where, f"{t.owner or t.name} names 'Scenario: {t.scenario}', which the spec does not "
                               "contain -- stale or invented")
        for s, req in scenarios.items():
            if not any(t.owner for t in by_scenario.get(s, [])):
                res.add("impl/tests", f"no test's docstring is 'Scenario: {s}' (requirement '{req}')")

        if run:
            records, crash = run_tests(impl)
            if records is None:
                res.add("impl/tests", crash)
            else:
                judge_outcomes(res, records, scenarios, allow_skips)

    task_file = change / "tasks.md"
    if task_file.is_file():
        for done, text in tasks(read(task_file)):
            if not done:
                res.add(rel(task_file, answer), f"unticked: {text}")

    for rule in rubric.get("impl_rules", []):
        judge_rule(res, impl, rule)
    return res


def judge_outcomes(res: StageResult, records: list[dict], scenarios: dict[str, str], allow_skips: bool) -> None:
    if not records:
        res.add("impl/tests", "no tests ran -- tests must be unittest.TestCase methods in impl/tests/test_*.py")
        return
    for r in records:
        if r["id"].startswith("unittest.loader._FailedTest"):
            res.add("impl/tests", f"could not import {r['id'].rsplit('.', 1)[-1]}: {_last_line(r['detail'])}")
        elif r["outcome"] in ("fail", "error") and not r["scenario"]:
            res.add("impl/tests", f"{r['id']} {r['outcome']}s: {_last_line(r['detail'])}")
    skipped: list[str] = []
    for s in scenarios:
        mine = [r for r in records if r["scenario"] == s]
        if not mine or any(r["outcome"] == "pass" for r in mine) and not any(r["outcome"] in ("fail", "error") for r in mine):
            continue  # missing tags are reported statically
        bad = next((r for r in mine if r["outcome"] in ("fail", "error")), None)
        if bad:
            res.add("impl/tests", f"Scenario '{s}': {bad['id'].rsplit('.', 2)[-2]}.{bad['id'].rsplit('.', 1)[-1]} "
                                  f"{bad['outcome']}s: {_last_line(bad['detail'])}")
        else:
            skipped.append((s, mine[0]["detail"] or "no reason given"))
    module_skips = [r for r in records if r["outcome"] == "skip" and not r["scenario"]]
    if skipped or module_skips:
        # A skipped scenario was not exercised. That is fine on a CI machine
        # without an optional dependency, and not fine as "done".
        by_reason: dict[str, list[str]] = defaultdict(list)
        for s, reason in skipped:
            by_reason[reason].append(f"'{s}'")
        what = "; ".join(f"{len(v)} scenario(s) because '{k}': {', '.join(v)}" for k, v in by_reason.items())
        what = what or f"{len(module_skips)} untagged test(s)"
        if allow_skips:
            res.notes.append(f"not exercised (skipped): {what} -- run where the dependency is installed before calling it done")
        else:
            res.add("impl/tests", f"not exercised (skipped): {what} -- install what they need, "
                                  "or pass --allow-skips to accept that knowingly")


def mcp_smoke(impl: Path, rule: dict) -> list[str]:
    """Talk to the server the way a real MCP client does, over stdio.

    Added after a Haiku trial produced a server whose own tests all passed
    and which no MCP client could use: replies had no id, notifications got
    answers, tools/list did not exist. Tests written by the same model that
    wrote the server share its misunderstanding; a protocol check does not.
    Messages go one at a time with stdin held open, because an SDK-based
    server may cancel in-flight work when stdin closes.
    """
    import queue
    import threading

    entry = impl / rule["mcp_smoke"]
    if not entry.is_file():
        return [f"no {rule['mcp_smoke']} to start"]
    proc = subprocess.Popen(
        [sys.executable, str(entry), "--root", str(impl)], cwd=str(impl),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8", errors="replace",
    )
    lines: "queue.Queue[str | None]" = queue.Queue()

    def pump() -> None:
        for line in proc.stdout:
            lines.put(line)
        lines.put(None)

    threading.Thread(target=pump, daemon=True).start()
    problems: list[str] = []
    stray: list[str] = []

    def send(msg: dict) -> None:
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    def reply(mid: int) -> dict | None:
        """The next message; anything else that arrives first is stray."""
        deadline = 10.0
        while True:
            try:
                line = lines.get(timeout=deadline)
            except queue.Empty:
                problems.append(f"no reply to request id {mid} within 10 s")
                return None
            if line is None:
                problems.append(f"server exited before replying to id {mid}")
                return None
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                problems.append(f"wrote a non-JSON line to stdout: {line.strip()[:80]!r}")
                continue
            if msg.get("id") == mid:
                if msg.get("jsonrpc") != "2.0":
                    problems.append(f"reply to id {mid} lacks \"jsonrpc\": \"2.0\"")
                return msg
            stray.append(line.strip()[:100])
            if msg.get("id") is None:
                problems.append(f"sent a message with no id (a reply must echo the request id): {line.strip()[:100]!r}")
                return None

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": rule["protocol"], "capabilities": {},
                         "clientInfo": {"name": "spec_fidelity", "version": "1"}}})
        init = reply(1)
        if init is not None:
            version = (init.get("result") or {}).get("protocolVersion")
            if version != rule["protocol"]:
                problems.append(f"initialize: protocolVersion {version!r}, expected {rule['protocol']!r}")
            send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            listed = reply(2)
            if listed is not None:
                if stray:
                    problems.append(f"answered a notification (JSON-RPC forbids it): {stray[0]!r}")
                tools = ((listed.get("result") or {}).get("tools")) if isinstance(listed.get("result"), dict) else None
                if not isinstance(tools, list):
                    problems.append(f"tools/list: no result.tools list (got {json.dumps(listed)[:100]})")
                else:
                    names = sorted(t.get("name", "") for t in tools if isinstance(t, dict))
                    if names != sorted(rule["tools"]):
                        problems.append(f"tools/list: tools {names}, expected {sorted(rule['tools'])}")
                    if any("inputSchema" not in t for t in tools if isinstance(t, dict)):
                        problems.append("tools/list: every tool needs an inputSchema")
                send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                      "params": {"name": "no_such_tool", "arguments": {}}})
                unknown = reply(3)
                # Either form is valid protocol: the 2025-06-18 spec shows a
                # -32602 error, the MCP Python SDK 2.x returns an isError
                # result. Which one the product owner wants is the learner's
                # own scenario test's business; this check is only "can a
                # client talk to it".
                if unknown is not None:
                    code = (unknown.get("error") or {}).get("code")
                    is_error = (unknown.get("result") or {}).get("isError") is True
                    if code != rule["unknown_tool_code"] and not is_error:
                        problems.append(f"tools/call of an unknown tool: expected error {rule['unknown_tool_code']} "
                                        f"or an isError result, got {json.dumps(unknown)[:100]}")
    finally:
        try:
            proc.stdin.close()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    return problems


def judge_rule(res: StageResult, impl: Path, rule: dict) -> None:
    if "mcp_smoke" in rule:
        for problem in mcp_smoke(impl, rule):
            res.add(f"impl/{rule['mcp_smoke']}", f"{rule['label']}: {problem}")
        return
    files = sorted(impl.glob(rule["glob"]))
    where = f"impl/{rule['glob']}"
    if not files:
        res.add("impl/", f"no file matches {rule['glob']} ({rule['label']})")
        return
    blob = "\n".join(prepared(f) for f in files)
    if "last" in rule:
        # Only the final FROM builds the image; only the final USER runs it.
        lines = [l.strip() for l in blob.splitlines() if re.match(rule["last"], l.strip())]
        if not lines:
            res.add(where, f"{rule['label']}: no line matches /{rule['last']}/")
            return
        blob = lines[-1]
    for pattern in rule.get("must_match", []):
        if not re.search(pattern, blob, re.MULTILINE):
            res.add(where, f"{rule['label']}: expected /{pattern}/")
    for pattern in rule.get("must_not_match", []):
        m = re.search(pattern, blob, re.MULTILINE)
        if m:
            res.add(where, f"{rule['label']}: found '{m.group(0)}'")


TITLES = {
    "prd": "PRD is OpenSpec-ready",
    "spec": "OpenSpec change is valid and traces to the PRD",
    "build": "Implementation is faithful to the spec",
}


def judge(target: Path, stages: tuple[str, ...] = STAGES, run_tests: bool = True,
          allow_skips: bool = False) -> list[StageResult]:
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
        if name == "prd":
            r = judge_prd(target, rubric)
        elif name == "spec":
            r = judge_spec(target, rubric)
        else:
            r = judge_build(target, rubric, run=run_tests, allow_skips=allow_skips)
        results.append(r)
        if not r.ok:
            blocked = name
    return results


HINTS = {
    "prd": "interrogate ticket.md (the product owner's answers are in stakeholder-answers.md) and write prd.md -- lesson 3, steps 1-2",
    "spec": "turn prd.md into openspec/changes/<id>/ -- lesson 3, step 3",
    "build": "build impl/ test-first, one unittest test per '#### Scenario:' -- lesson 3, step 4",
}


def grade(answer: Path) -> tuple[bool, str, str]:
    """``(ok, message, hint)`` for tutorials/check.py.

    Skips are allowed here, and only here: CI has no LangChain, and the
    reference chatbot's chain scenarios must not fail the build for it. The
    note says so every time. The CLI -- what a learner and HARNESS.md run --
    does not allow them.
    """
    results = judge(answer, allow_skips=True)
    if all(r.ok for r in results):
        notes = "".join(f" ({n})" for r in results for n in r.notes)
        return True, f"prd, spec and build all faithful{notes} -- now run the agent-backed half (lesson 3, step 5)", ""
    failed = next(r for r in results if not r.ok and not r.skipped)
    shown = "; ".join(str(f) for f in failed.findings[:3])
    more = len(failed.findings) - 3
    suffix = f" (+{more} more)" if more > 0 else ""
    shown_path = rel(answer, TRACK.parents[1])
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
    parser.add_argument("target", type=Path, help="an exercise folder, a workspace, or a solution/ folder")
    parser.add_argument("--stage", choices=(*STAGES, "all"), default="all")
    parser.add_argument("--no-tests", action="store_true", help="skip running impl/tests")
    parser.add_argument("--allow-skips", action="store_true",
                        help="accept skipped scenario tests (reported as a note, not a finding)")
    # Claude Code aborts a slash command whose `!` shell line exits non-zero,
    # so a command that runs the judge in order to explain its failures would
    # never see them. Same escape hatch linters use.
    parser.add_argument("--exit-zero", action="store_true", help="exit 0 even when a stage fails")
    args = parser.parse_args(argv)
    stages = STAGES if args.stage == "all" else (args.stage,)
    results = judge(args.target.resolve(), stages, run_tests=not args.no_tests, allow_skips=args.allow_skips)
    sys.stdout.reconfigure(encoding="utf-8")
    print(report(results))
    return 0 if args.exit_zero or all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
