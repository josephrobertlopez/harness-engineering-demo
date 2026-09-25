"""One command to get a machine ready for track 50.

    python tutorials/50-spec-fidelity/setup.py                  # check, and make the workspaces
    python tutorials/50-spec-fidelity/setup.py --install        # also install what is missing
    python tutorials/50-spec-fidelity/setup.py --root ~/work/fidelity

Without --install nothing is installed and nothing outside --root is
touched: it reports what is present and what each missing piece costs you,
then creates one workspace per exercise with start.py.

With --install it also:

- creates <root>/.venv with langchain-core, langchain-anthropic and mcp, and
  builds the workspaces with that interpreter -- the /fidelity:* commands
  and the judge then run tests where LangChain is importable, so exercise
  2's chain scenarios are exercised instead of skipped;
- installs the OpenSpec CLI with npm, if npm is present;
- adds and installs the ai-literacy-superpowers plugin, if claude is present.

Each install is a separate command, printed before it runs, and a failure
is reported and skipped rather than stopping the rest: one missing tool
should not cost you the others.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

TRACK = Path(__file__).resolve().parent
EXERCISES = {"01": "ops-1432", "02": "sup-88", "03": "devx-311"}
PY_PACKAGES = ["langchain-core", "langchain-anthropic", "mcp"]
PLUGIN_MARKETPLACE = "Habitat-Thinking/ai-literacy-superpowers"
PLUGIN = "ai-literacy-superpowers"

# What each tool is for, so a missing one is reported as a consequence
# rather than a bare name.
TOOLS = [
    ("claude", "required: you do the exercises in Claude Code"),
    ("git", "exercise 3 (the server wraps git), and its judge probes"),
    ("rg", "exercise 3 (the server wraps ripgrep); without it the rg probes are skipped"),
    ("docker", "exercise 1, to build and run the image for real (the judge does not need it)"),
    ("npm", "optional: installs the OpenSpec CLI for /opsx:* and `openspec validate`"),
    ("openspec", "optional: /opsx:propose and `openspec validate --strict`"),
]


def check() -> dict[str, bool]:
    present = {}
    print(f"python {sys.version.split()[0]}  {'ok' if sys.version_info >= (3, 12) else 'TOO OLD -- need 3.12+'}")
    for name, why in TOOLS:
        found = shutil.which(name) is not None
        present[name] = found
        print(f"{name:9} {'ok' if found else 'missing'}{'' if found else '  -- ' + why}")
    return present


def run(cmd: list[str], **kw) -> bool:
    print("  $ " + " ".join(cmd))
    try:
        proc = subprocess.run(cmd, **kw)
    except OSError as exc:
        print(f"    failed: {exc}")
        return False
    if proc.returncode != 0:
        print(f"    failed with exit code {proc.returncode} -- skipping, the rest still runs")
    return proc.returncode == 0


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def install(root: Path, present: dict[str, bool]) -> Path | None:
    """Returns the venv interpreter if the venv is usable, else None."""
    venv = root / ".venv"
    python: Path | None = None
    print("\n-- Python packages (in a venv, never the system Python)")
    if venv_python(venv).is_file() or run([sys.executable, "-m", "venv", str(venv)]):
        if run([str(venv_python(venv)), "-m", "pip", "install", "--quiet", *PY_PACKAGES]):
            python = venv_python(venv)

    print("\n-- OpenSpec CLI")
    if present.get("openspec"):
        print("  already installed")
    elif present.get("npm"):
        run(["npm", "install", "-g", "@fission-ai/openspec@latest"])
    else:
        print("  skipped: no npm (Node 20.19+). Optional -- you can write the change by hand.")

    print("\n-- ai-literacy-superpowers plugin (the agent half of the judge)")
    if present.get("claude"):
        run(["claude", "plugin", "marketplace", "add", PLUGIN_MARKETPLACE])
        run(["claude", "plugin", "install", PLUGIN])
    else:
        print("  skipped: no claude CLI")
    return python


def make_workspaces(root: Path, python: Path | None) -> list[Path]:
    made = []
    print(f"\n-- Workspaces in {root}")
    for num, name in EXERCISES.items():
        dest = root / name
        if dest.exists() and any(dest.iterdir()):
            print(f"  {name}: exists, left alone")
            made.append(dest)
            continue
        # start.py embeds the interpreter that runs it into the slash
        # commands and HARNESS.md, so run it with the venv when there is one.
        interpreter = str(python) if python else sys.executable
        cmd = [interpreter, str(TRACK / "start.py"), num, str(dest)]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode == 0:
            print(f"  {name}: ready")
            made.append(dest)
        else:
            print(f"  {name}: failed -- {(proc.stderr or proc.stdout).strip()[-200:]}")
    return made


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path.home() / "fidelity",
                        help="where the workspaces go (default: ~/fidelity); must be outside this repo")
    parser.add_argument("--install", action="store_true", help="install what is missing (see above)")
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    repo = TRACK.parents[1]
    if root == repo or repo in root.parents:
        raise SystemExit("put --root outside this repo, or Claude can read the solutions")
    if sys.version_info < (3, 12):
        raise SystemExit("Python 3.12+ is required")

    print("-- This machine")
    present = check()
    root.mkdir(parents=True, exist_ok=True)
    python = install(root, present) if args.install else None
    if python is None and (root / ".venv").is_dir() and venv_python(root / ".venv").is_file():
        python = venv_python(root / ".venv")
    made = make_workspaces(root, python)

    print("\n-- Next")
    if not present.get("claude"):
        print("  install Claude Code first: https://code.claude.com/docs")
    if made:
        print(f"  cd {made[0]} && claude")
        print("  then type /fidelity:interrogate -- you are the product owner; your notes are in")
        print(f"  {made[0].parent / (made[0].name + '.stakeholder-answers.md')} (keep them out of Claude's reach)")
    print(f"  read first: {(TRACK / 'lesson-04-work-backwards.md').as_posix()}")
    return 0 if len(made) == len(EXERCISES) else 1


if __name__ == "__main__":
    sys.exit(main())
