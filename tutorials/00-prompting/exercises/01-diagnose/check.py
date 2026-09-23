"""Exercise 1: name the failure before trying to fix it."""

from __future__ import annotations

import re

from exercise_api import Context, Result

TITLE = "Diagnose three bad outputs by anti-pattern and rubric dimension"

#: scenario -> (anti-pattern, the rubric dimension it primarily damages)
EXPECTED = {
    "1": ("AP7", "T"),
    "2": ("AP5", "H"),
    "3": ("AP1", "T"),
}

TEMPLATE = """1. AP?  dimension: ?
2. AP?  dimension: ?
3. AP?  dimension: ?
"""


def check(ctx: Context) -> Result:
    text = ctx.read_answer("answers.md")
    if text is None:
        return Result.failed(
            "no answers.md",
            f"create {ctx.answer('answers.md')} with one line per scenario:\n{TEMPLATE}",
        )

    wrong: list[str] = []
    for scenario, (pattern, dimension) in EXPECTED.items():
        line = _line_for(text, scenario)
        if line is None:
            wrong.append(f"scenario {scenario}: no answer found")
            continue
        got_ap = _first(r"\bAP([1-7])\b", line)
        got_dim = _first(r"\b(?:dimension:\s*)?([PiΠHMIT])\b", line)
        if got_ap != pattern[2:]:
            wrong.append(f"scenario {scenario}: expected {pattern}, read AP{got_ap or '?'}")
        elif got_dim is None or got_dim.upper() not in {dimension, "Π"} and got_dim != dimension:
            wrong.append(f"scenario {scenario}: expected dimension {dimension}, read {got_dim or '?'}")

    if wrong:
        return Result.failed(
            "; ".join(wrong),
            "re-read lesson 3 -- each anti-pattern lists the dimension it hits",
        )
    return Result.passed("all three scenarios correctly diagnosed")


def _line_for(text: str, scenario: str) -> str | None:
    for line in text.splitlines():
        if line.strip().startswith(scenario):
            return line
    return None


def _first(pattern: str, line: str) -> str | None:
    m = re.search(pattern, line)
    return m.group(1) if m else None
