"""Exercise 2: a perfect score that memorised the answers is still a failure."""

from __future__ import annotations

import re

from exercise_api import Context, Result, score_skills_dir

TITLE = "Pass every held-out task without hardcoding a single answer"

#: The values the test split expects. A skill containing any of these has
#: written down the answer rather than the rule, and would do nothing for a
#: record it has not already seen.
FORBIDDEN_LITERALS = (
    "2026-03-07T06:30:12Z",
    "REC-4843:reconcile",
    "40.48",
    "okonkwo",
    "reversed",
)

#: Train-split values are fine -- worked examples are good writing, and the
#: real Skill Proposer used them. Only the held-out answers are off limits.


def check(ctx: Context) -> Result:
    skills = ctx.answer("skills")
    if not skills.is_dir() or not any(
        d.is_dir() and (d / "SKILL.md").is_file() for d in skills.iterdir()
    ):
        return Result.failed(
            "no skill found",
            f"create {skills / '<your-skill-name>' / 'SKILL.md'}",
        )

    text = "\n".join(
        p.read_bytes().decode("utf-8", "replace")
        for p in sorted(skills.rglob("*.md"))
    )

    leaked = [lit for lit in FORBIDDEN_LITERALS if _contains(text, lit)]
    scored = score_skills_dir(skills, ctx.scratch)

    if leaked:
        return Result.failed(
            f"scored {scored:.3f}, but the skill hardcodes: {', '.join(leaked)}",
            "state the rule instead of the answer -- `<record_id>:<operation>` "
            "rather than `REC-4843:reconcile`. Worked examples using *train* "
            "records are fine.",
        )

    if scored >= 1.0:
        return Result.passed(f"all 5 held-out tasks pass, no answers hardcoded ({scored:.3f})")

    return Result.failed(
        f"no hardcoded answers (good) but scored {scored:.3f}; need 1.000",
        "run eval with --skills-dir to see which rules are still missing",
    )


def _contains(haystack: str, literal: str) -> bool:
    return re.search(re.escape(literal), haystack, re.IGNORECASE) is not None
