"""Exercise 2: does the instruction contain enough to act on?"""

from __future__ import annotations

from exercise_api import Context, Result, score_skills_dir

TITLE = "Rewrite two vague rules so an agent can actually follow them"


def check(ctx: Context) -> Result:
    rules = ctx.answer("rules")
    target = rules / "instructions" / "SKILL.md"
    if not target.is_file():
        return Result.failed(
            "no rewrite found",
            f"create {target} -- see the exercise README for the format",
        )

    scored = score_skills_dir(rules, ctx.scratch)
    passing = round(scored * 5)

    # Both rewrites landing means iso_z and round_even pass. Baseline is 0/5,
    # so anything above zero is the instruction carrying real information.
    if passing >= 2:
        return Result.passed(f"{passing}/5 tasks now pass ({scored:.3f}) -- both rules landed")
    if passing == 1:
        return Result.failed(
            f"only {passing}/5 passing -- one rewrite is actionable, the other is not",
            "run eval with --skills-dir and read which failure remains",
        )
    return Result.failed(
        f"{passing}/5 passing -- neither rewrite is actionable yet",
        "name the transformation, not the topic. 'Handle dates properly' says "
        "what the rule is about; it does not say what to do.",
    )
