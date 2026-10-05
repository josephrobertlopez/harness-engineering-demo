"""Command-line interface for specgate: `specgate check`."""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from specgate import __version__, l0_schema, l1_static, l2_trace, l3_run, l4_cov, l5_mut
from specgate.l0_schema import parse_prd
from specgate.trace import generate_trace

Findings = list[dict[str, Any]]

LAST_LAYER = 6
DEFAULT_LAYERS = "L0-L5"
_SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache", ".ruff_cache"}
_GIT_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")


def git_env() -> dict[str, str]:
    """os.environ without the variables git sets inside hooks.

    Inherited GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE would point any git
    call at the invoking repository instead of the one we name.
    """
    return {k: v for k, v in os.environ.items() if k not in _GIT_VARS}


def _walk(base: str) -> list[Path]:
    """Every file under base, sorted, skipping tool and cache directories."""
    found: list[Path] = []
    for root, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
        found.extend(Path(root) / name for name in sorted(files))
    return found


def find_prd_file(change_dir: str) -> str | None:
    """First prd.md under change_dir (sorted, shallowest path first), else None."""
    candidates = sorted(
        (p for p in _walk(change_dir) if p.name == "prd.md"),
        key=lambda p: (len(p.parts), str(p)),
    )
    return str(candidates[0]) if candidates else None


def extract_ac_ids(prd_path: str) -> set[str]:
    """AC ids declared in the PRD frontmatter; empty when it cannot be parsed."""
    frontmatter, _error = parse_prd(prd_path)
    acs = (frontmatter or {}).get("acs") or []
    return {str(ac["id"]) for ac in acs if isinstance(ac, dict) and "id" in ac}


def _marker_dirs(root: str) -> tuple[list[str], list[str]]:
    src: set[str] = set()
    tests: set[str] = set()
    for locs in l2_trace.scan_markers([root], [root]).values():
        for loc in locs:
            (src if loc.marker_type == "implements" else tests).add(str(Path(loc.file).parent))
    return sorted(src), sorted(tests)


def find_source_and_test_dirs(base: str, fallback: str | None = None) -> tuple[list[str], list[str]]:
    """Directories holding `# implements:` (source) and `# covers:` (test) markers.

    Searched under base; when it holds no markers, under `fallback` (the repo
    root, for a change directory that contains only the PRD).
    """
    for root in (base, fallback):
        if root is not None:
            src, tests = _marker_dirs(root)
            if src or tests:
                return src, tests
    return [], []


def _py_files(dirs: list[str]) -> list[str]:
    return [str(p) for d in dirs for p in l2_trace.iter_py_files(d)]


def _red(findings: Findings) -> tuple[Findings, bool]:
    return findings, bool(findings)


def check_layer(
    layer: int,
    change_dir: str | None = None,
    junit_path: str | None = None,
    cwd: str | None = None,
    only: frozenset[str] | None = None,
) -> tuple[Findings, bool]:
    """Run one layer; returns (findings, has_failures).

    L6 (the model debate) is never run from the CLI and returns no findings.
    `only` (normalised paths, used by --staged) restricts the layer to those
    files: layers that run whole directories are skipped when none of the
    files is relevant, and findings in other files are dropped.
    """
    base = change_dir or cwd or "."
    prd = find_prd_file(base)
    if only is not None and not _touches(only):
        return [], False
    findings, _ = _run_layer(layer, base, prd, change_dir, junit_path, cwd, only)
    if only is not None:
        findings = [f for f in findings if os.path.realpath(f["file"]) in only]
    return _red(findings)


def _touches(only: frozenset[str]) -> bool:
    """True when a staged file is a python or markdown file."""
    return any(p.endswith((".py", ".md")) for p in only)


def _run_layer(
    layer: int,
    base: str,
    prd: str | None,
    change_dir: str | None,
    junit_path: str | None,
    cwd: str | None,
    only: frozenset[str] | None,
) -> tuple[Findings, bool]:
    if layer == 0:
        if prd is None:
            return _red([{
                "rule": "SG006", "file": base, "line": 0,
                "message": f"No prd.md found under {base}",
            }])
        spec_root = Path(cwd or ".")
        change = Path(base).name if change_dir and (spec_root / "openspec").is_dir() else None
        return _red(l0_schema.check(prd, change, str(spec_root) if change else None))

    src_dirs, test_dirs = find_source_and_test_dirs(base, cwd)
    if layer == 1:
        md = [prd] if prd else []
        py = sorted(set(_py_files([base] + src_dirs + test_dirs)))
        if only is not None:
            py = [p for p in py if os.path.realpath(p) in only]
            md = [m for m in md if os.path.realpath(m) in only]
        return _red(l1_static.check(py, md_paths=md))

    if prd is None or layer > 5:
        return [], False
    ac_ids = extract_ac_ids(prd)

    if layer == 2:
        return _red(l2_trace.check(ac_ids, _py_files(src_dirs), _py_files(test_dirs)))
    if layer == 3:
        if junit_path is not None:
            return _red(l3_run.check(ac_ids, src_dirs, test_dirs, junit_path))
        with tempfile.TemporaryDirectory() as tmp:
            return _red(l3_run.check(ac_ids, src_dirs, test_dirs, os.path.join(tmp, "junit.xml")))
    if layer == 4:
        return _red(l4_cov.check(ac_ids, src_dirs, test_dirs))
    return _red(l5_mut.check(ac_ids, src_dirs, test_dirs))


def parse_layers(spec: str) -> list[int] | None:
    """Parse 'L2' or 'L0-L5' into layer numbers; None when invalid."""
    match = re.fullmatch(r"L(\d+)(?:-L(\d+))?", spec)
    if not match:
        return None
    first = int(match.group(1))
    last = int(match.group(2) or first)
    if first > last or last > LAST_LAYER:
        return None
    return list(range(first, last + 1))


def staged_files(repo: str) -> list[str]:
    """Paths staged under `repo`, relative to it (hook git variables stripped)."""
    result = subprocess.run(
        ["git", "-C", repo, "diff", "--cached", "--name-only", "--relative"],
        capture_output=True, text=True, check=False, env=git_env(),
    )
    return result.stdout.split() if result.returncode == 0 else []


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="specgate", description="Specification gate for PRD validation"
    )
    parser.add_argument("--version", action="version", version=f"specgate {__version__}")
    sub = parser.add_subparsers(dest="command")
    check = sub.add_parser("check", help="Run the gate layers; stop at the first red")
    check.add_argument("--change", help="change directory holding prd.md (default: cwd)")
    check.add_argument("--layers", default=DEFAULT_LAYERS, help="e.g. L2 or L0-L5")
    check.add_argument("--staged", action="store_true",
                       help="skip the gate when nothing is staged")
    check.add_argument("--output", default="trace.json", help="trace.json path")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Exit 0 green, 2 bad arguments, 10+L when layer L is red."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    layers = parse_layers(args.layers)
    if layers is None:
        sys.stderr.write(f"specgate: invalid --layers {args.layers!r}" + "\n")
        return 2
    if layers == [LAST_LAYER]:
        sys.stderr.write("specgate: L6 is not run by the CLI; use run_debate()\n")
        return 2
    if LAST_LAYER in layers:
        sys.stderr.write("specgate: warning: L6 is not run by the CLI; use run_debate()\n")

    base = args.change or "."
    only: frozenset[str] | None = None
    if args.staged:
        only = frozenset(os.path.realpath(os.path.join(base, p)) for p in staged_files(base))
        if not only:
            sys.stderr.write("specgate: nothing staged\n")
            return 0

    for layer in layers:
        findings, red = check_layer(layer, change_dir=args.change, cwd=".", only=only)
        if red:
            for f in findings:
                sys.stderr.write(f"L{layer} {f['rule']} {f['file']}:{f['line']} {f['message']}\n")
            return 10 + layer

    prd = find_prd_file(base)
    if prd is not None:
        src_dirs, test_dirs = find_source_and_test_dirs(base, ".")
        generate_trace(extract_ac_ids(prd), src_dirs, test_dirs, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
