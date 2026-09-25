"""Set up a clean workspace for one track-50 exercise, outside the repo.

    python tutorials/50-spec-fidelity/start.py 01-docker-rest ~/fidelity/ops-1432
    python tutorials/50-spec-fidelity/start.py 01 ~/fidelity/backwards --with-solution

Why a copy and not the exercise folder itself: Claude Code reads whatever is
in its working directory. Started inside the repo, it can open ``solution/``
and ``stakeholder-answers.md`` -- and a model that has seen the answer will
"interrogate" you with suspiciously perfect questions. The copy contains
only what a developer handed this ticket would actually have.

What lands in the workspace:

    ticket.md          the vague ticket -- your only brief
    .fidelity.json     names the exercise, so the judge can find its rubric
    HARNESS.md         how the work is judged, paths rewritten
    openspec/config.yaml   teaches /opsx:propose the PRD trace convention
    .claude/commands/fidelity/   the lesson-3 prompts as slash commands:
                       /fidelity:interrogate, :prd, :review-prd, :propose,
                       :build, :judge, :enforce
    faq.md             (exercise 2 only) the ticket's attachment
    personas/          Interrogator, Adversary, Implementer, for Claude to read

What deliberately does not:

    solution/                   the reference answer
    rubric.json                 its facts *are* the product owner's answers;
                                the judge reads it from the repo instead
    stakeholder-answers.md      written next to the workspace, not inside it:
                                you are the product owner; Claude has to ask
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

TRACK = Path(__file__).resolve().parent
REPO = TRACK.parents[1]
EXERCISES = TRACK / "exercises"
GIVEN = ("ticket.md", "faq.md")
PERSONAS = ("spec-interrogator", "spec-adversary", "spec-implementer")
JUDGE_IN_HARNESS = "python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE"


def start(exercise: str, dest: Path, with_solution: bool = False) -> list[str]:
    matches = sorted(d for d in EXERCISES.iterdir() if d.is_dir() and d.name.startswith(exercise))
    if len(matches) != 1:
        names = ", ".join(d.name for d in sorted(EXERCISES.iterdir()) if d.is_dir())
        raise SystemExit(f"pick one exercise: {names}")
    source = matches[0]
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"{dest} already exists and is not empty -- pick a new folder")
    dest.mkdir(parents=True, exist_ok=True)

    made: list[str] = []
    for name in GIVEN:
        if (source / name).is_file():
            shutil.copyfile(source / name, dest / name)
            made.append(name)

    (dest / ".fidelity.json").write_text(json.dumps({"exercise": source.name}) + "\n", encoding="utf-8", newline="\n")
    made.append(".fidelity.json")

    python = Path(sys.executable).as_posix()
    judge = (TRACK / "spec_fidelity.py").as_posix()
    harness = (source / "HARNESS.md").read_text(encoding="utf-8")
    harness = harness.replace(JUDGE_IN_HARNESS, f"{python} {judge} .")
    (dest / "HARNESS.md").write_text(harness, encoding="utf-8", newline="\n")
    made.append("HARNESS.md")

    (dest / "openspec").mkdir()
    shutil.copyfile(TRACK / "openspec-config.yaml", dest / "openspec" / "config.yaml")
    made.append("openspec/config.yaml")

    rubric = json.loads((source / "rubric.json").read_text(encoding="utf-8"))
    # The ticket's own vague words: telling the model which words to avoid
    # reveals nothing the ticket does not already say.
    vague = ", ".join(f'"{w}"' for w in rubric["vague_terms"])
    # Filled in with this interpreter and this judge, so the commands work
    # whether the machine calls Python `python`, `python3` or a venv path.
    commands = dest / ".claude" / "commands" / "fidelity"
    commands.mkdir(parents=True)
    for prompt in sorted((TRACK / "prompts").glob("*.md")):
        if prompt.name == "README.md":
            continue  # documentation for maintainers; as a command it would be /fidelity:README
        text = prompt.read_text(encoding="utf-8")
        text = text.replace("{{PYTHON}}", python).replace("{{JUDGE}}", judge).replace("{{VAGUE_TERMS}}", vague)
        (commands / prompt.name).write_text(text, encoding="utf-8", newline="\n")
    made.append(".claude/commands/fidelity/  (/fidelity:interrogate ... /fidelity:enforce)")

    (dest / "personas").mkdir()
    for persona in PERSONAS:
        shutil.copyfile(REPO / "personas" / f"{persona}.persona.md", dest / "personas" / f"{persona}.persona.md")
    made.append("personas/")

    if with_solution:
        # For lesson 4: a copy of the finished chain to read backwards and
        # break on purpose, without touching the one in the repo.
        for item in sorted((source / "solution").iterdir()):
            target = dest / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copyfile(item, target)
        made.append("prd.md, openspec/changes/, impl/  (the reference solution)")

    answers = dest.parent / f"{dest.name}.stakeholder-answers.md"
    shutil.copyfile(source / "stakeholder-answers.md", answers)
    return made + [f"(outside) {answers}"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("exercise", help="01, 02, 03, or a full exercise folder name")
    parser.add_argument("dest", type=Path, help="a new folder outside this repo")
    parser.add_argument("--with-solution", action="store_true", help="also copy the reference solution in (lesson 4)")
    args = parser.parse_args(argv)
    dest = args.dest.expanduser().resolve()
    if dest == REPO or REPO in dest.parents:
        raise SystemExit("put the workspace outside this repo, or Claude can read solution/")
    if " " in sys.executable or " " in str(TRACK):
        # The slash commands embed both paths unquoted in `!` lines and in
        # allowed-tools patterns, where a space splits the command.
        print("warning: the Python or repo path contains a space; the /fidelity:* commands "
              "that run the judge may fail. Use a path without spaces if they do.")
    for line in start(args.exercise, dest, with_solution=args.with_solution):
        print(f"  {line}")
    print(f"\ncd {dest} && claude")
    print(f"judge any time: python {(TRACK / 'spec_fidelity.py').as_posix()} {dest.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
