"""L5 layer: mutation testing of each AC's implementation with AST transformations."""

import ast
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from specgate.l2_trace import _extract_functions, get_marker_map

MUTATION_TYPES = ("cmp_flip", "bool_flip", "return_none", "arith_swap")

_CMP_FLIP: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Lt: ast.GtE,
    ast.LtE: ast.Gt,
    ast.Gt: ast.LtE,
    ast.GtE: ast.Lt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
}


class MutantGenerator(ast.NodeTransformer):
    """Apply one deterministic mutation of one type to the first eligible node."""

    def __init__(self, target_lines: set[int], mutation_type: str, seed: int):
        self.target_lines = target_lines
        self.mutation_type = mutation_type
        self.rng = random.Random(seed)
        self.mutated_line: int | None = None

    def _eligible(self, node: ast.expr | ast.stmt, mutation_type: str) -> bool:
        return (
            self.mutation_type == mutation_type
            and node.lineno in self.target_lines
            and self.mutated_line is None
        )

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        """Flip comparison operators (< <-> >=, > <-> <=, == <-> !=)."""
        if self._eligible(node, "cmp_flip"):
            new_ops = [_CMP_FLIP[type(op)]() if type(op) in _CMP_FLIP else op for op in node.ops]
            if new_ops != node.ops:
                self.mutated_line = node.lineno
                node.ops = new_ops
        return self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
        """Flip and <-> or."""
        if self._eligible(node, "bool_flip"):
            self.mutated_line = node.lineno
            node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
        return self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> ast.AST:
        """Replace a returned value with None."""
        if self._eligible(node, "return_none") and node.value is not None:
            self.mutated_line = node.lineno
            node.value = None
        return self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        """Swap + <-> -."""
        if self._eligible(node, "arith_swap") and isinstance(node.op, (ast.Add, ast.Sub)):
            self.mutated_line = node.lineno
            node.op = ast.Sub() if isinstance(node.op, ast.Add) else ast.Add()
        return self.generic_visit(node)


def _function_lines(source: str, qualname: str) -> set[int]:
    """Line numbers inside the function named by a marker qualname ('mod:Class.func')."""
    info = _extract_functions(source, "").get(qualname.split(":", 1)[1])
    if info is None:
        return set()
    return {child.lineno for child in ast.walk(info[1]) if hasattr(child, "lineno")}


def _generate_source_mutant(
    source: str, target_lines: set[int], mutation_type: str, seed: int
) -> tuple[str, int] | None:
    """Mutated source and the original line mutated, or None if nothing mutates."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    gen = MutantGenerator(target_lines, mutation_type, seed)
    new_tree = gen.visit(tree)
    if gen.mutated_line is None:
        return None
    ast.fix_missing_locations(new_tree)
    return ast.unparse(new_tree), gen.mutated_line


def _run_tests(test_dir: str, test_module: str) -> bool:
    """Run one unittest module in test_dir; True when all of it passes."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", test_module],
            cwd=test_dir,
            capture_output=True,
            timeout=10,
            text=True,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0


def _survives(impl_file: str, mutant_source: str, test_files: list[str]) -> bool:
    """True when every covering test module still passes against the mutant."""
    with tempfile.TemporaryDirectory() as tmp:
        for directory in sorted({Path(impl_file).parent, *(Path(t).parent for t in test_files)}):
            for py_file in sorted(directory.glob("*.py")):
                shutil.copy2(py_file, tmp)
        (Path(tmp) / Path(impl_file).name).write_text(mutant_source)
        return all(_run_tests(tmp, Path(t).stem) for t in test_files)


# implements: AC-6
def check(
    ac_ids: set[str], src_dirs: list[str], test_dirs: list[str]
) -> list[dict[str, Any]]:
    """SG501 for each mutant of an AC's implementation that its tests do not kill."""
    findings: list[dict[str, Any]] = []
    marker_map = get_marker_map(src_dirs, test_dirs)
    for ac_id in sorted(ac_ids):
        markers = marker_map.get(ac_id, [])
        test_files = sorted({m.file for m in markers if m.marker_type == "covers"})
        if not test_files:
            continue
        for impl in (m for m in markers if m.marker_type == "implements"):
            source = Path(impl.file).read_text()
            lines = _function_lines(source, impl.qualname)
            for mutation_type in MUTATION_TYPES:
                mutant = _generate_source_mutant(source, lines, mutation_type, 0)
                if mutant is None:
                    continue
                mutant_source, line = mutant
                if _survives(impl.file, mutant_source, test_files):
                    findings.append({
                        "rule": "SG501",
                        "file": impl.file,
                        "line": line,
                        "message": f"Surviving mutant in {impl.funcname}: "
                                   f"{mutation_type} at line {line}",
                    })
    findings.sort(key=lambda f: (f["file"], f["line"], f["rule"], f["message"]))
    return findings
