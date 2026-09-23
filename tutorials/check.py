"""Run tutorial exercise checks.

    python tutorials/check.py                        # everything
    python tutorials/check.py 30-skill-authoring     # one track
    python tutorials/check.py 30-skill-authoring/02  # one exercise

Exercises are discovered by convention: any
`tutorials/<track>/exercises/<id>/check.py` that defines `TITLE` and
`check(ctx) -> Result`. Nothing is registered centrally, so adding a lesson
does not mean editing this file.

The same discovery runs in the test suite, which is the point -- a lesson
that tells a learner to use a flag that no longer exists fails CI here
rather than wasting their afternoon.
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from exercise_api import Context, REPO_ROOT, Result  # noqa: E402

TUTORIALS = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class Exercise:
    track: str
    ident: str
    directory: Path
    title: str
    run: object

    @property
    def slug(self) -> str:
        return f"{self.track}/{self.ident}"


def discover(selector: str | None = None) -> list[Exercise]:
    found: list[Exercise] = []
    for check_py in sorted(TUTORIALS.glob("*/exercises/*/check.py")):
        directory = check_py.parent
        track = check_py.parents[2].name
        ident = directory.name
        if selector and not f"{track}/{ident}".startswith(selector.rstrip("/")):
            continue
        # A broken exercise is reported as a failing exercise, never an
        # exception. Raising here took down discovery of every *other*
        # exercise too -- a zero-byte file from an interrupted write made
        # three unrelated tests error out, which is a much worse signal than
        # one clear failure.
        try:
            module = _load(check_py, f"ex_{track}_{ident}".replace("-", "_"))
            run = getattr(module, "check", None)
            title = getattr(module, "TITLE", ident)
            if run is None:
                raise AttributeError("defines no check(ctx)")
        except Exception as exc:
            found.append(
                Exercise(
                    track=track,
                    ident=ident,
                    directory=directory,
                    title=f"(broken) {ident}",
                    run=_broken(check_py, exc),
                )
            )
            continue
        found.append(
            Exercise(track=track, ident=ident, directory=directory, title=title, run=run)
        )
    return found


def _broken(path: Path, exc: Exception):
    def run(_ctx: Context) -> Result:
        return Result.failed(
            f"{path.name} could not be loaded: {type(exc).__name__}: {exc}",
            "this is a repo bug, not your answer -- the exercise itself is broken",
        )

    return run


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_one(exercise: Exercise) -> Result:
    scratch = Path(tempfile.mkdtemp(prefix="wikiskill-ex-"))
    try:
        ctx = Context(exercise_dir=exercise.directory, scratch=scratch, repo_root=REPO_ROOT)
        result = exercise.run(ctx)
        if not isinstance(result, Result):
            return Result.failed(f"check() returned {type(result).__name__}, expected Result")
        return result
    except Exception as exc:  # a broken check is a failed check, not a crash
        return Result.failed(f"{type(exc).__name__}: {exc}")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selector", nargs="?", help="track, or track/exercise")
    args = parser.parse_args(argv)

    exercises = discover(args.selector)
    if not exercises:
        target = args.selector or "anywhere"
        print(f"no exercises found for {target}")
        return 1

    failures = 0
    for ex in exercises:
        result = run_one(ex)
        mark = "PASS" if result.ok else "FAIL"
        print(f"[{mark}] {ex.slug}  {ex.title}")
        if result.message:
            print(f"       {result.message}")
        if not result.ok:
            failures += 1
            if result.hint:
                print(f"       hint: {result.hint}")

    total = len(exercises)
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
