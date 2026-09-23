"""Exercise 1: close the loop -- write a skill, make the score move."""

from __future__ import annotations

from exercise_api import Context, Result, score_baseline, score_skills_dir

TITLE = "Write a skill that beats the baseline on the held-out split"

TASKS = 5


def check(ctx: Context) -> Result:
    skills = ctx.answer("skills")
    if not skills.is_dir() or not any(
        d.is_dir() and (d / "SKILL.md").is_file() for d in skills.iterdir()
    ):
        return Result.failed(
            "no skill found",
            f"create {skills / '<your-skill-name>' / 'SKILL.md'} "
            "-- the folder layout matters, --skills-dir expects <name>/SKILL.md",
        )

    baseline = score_baseline(ctx.scratch)
    scored = score_skills_dir(skills, ctx.scratch)
    gained = round((scored - baseline) * TASKS)

    if gained >= 2:
        return Result.passed(
            f"baseline {baseline:.3f} -> {scored:.3f} ({gained} more tasks passing)"
        )
    return Result.failed(
        f"baseline {baseline:.3f} -> {scored:.3f} ({gained} more tasks passing; need 2)",
        "run the eval command from lesson 2 -- it names each remaining failure "
        "and the exact value it expected",
    )
