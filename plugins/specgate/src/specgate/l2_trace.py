"""L2 layer: AST-based AC marker tracing and validation."""

import ast
import tokenize
import io
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MarkerLocation:
    """Represents a marker location in source code."""
    file: str
    funcname: str
    line: int
    ac_id: str
    marker_type: str  # 'implements' or 'covers'


def _tokenize_comments(source: str) -> Dict[int, str]:
    """Extract comments and their line numbers from source code.

    Returns a dict mapping line number to comment text (without # prefix).
    """
    comments = {}
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok_type, tok_string, start, end, line in tokens:
            if tok_type == tokenize.COMMENT:
                # Remove the # and strip whitespace
                comment_text = tok_string[1:].strip()
                comments[start[0]] = comment_text
    except tokenize.TokenError:
        # Handle incomplete tokens gracefully
        pass
    return comments


def _parse_marker(comment: str) -> Optional[Tuple[str, str]]:
    """Parse a marker comment.

    Returns (marker_type, ac_id) if valid, None otherwise.
    marker_type is 'implements' or 'covers'
    """
    comment = comment.strip()

    # Check for "implements: AC-X" or "covers: AC-X"
    if comment.startswith('implements:'):
        rest = comment[len('implements:'):].strip()
        ac_id = rest.split()[0] if rest else None
        if ac_id:
            return ('implements', ac_id)
    elif comment.startswith('covers:'):
        rest = comment[len('covers:'):].strip()
        ac_id = rest.split()[0] if rest else None
        if ac_id:
            return ('covers', ac_id)

    return None


def _extract_functions(source: str, filepath: str) -> Dict[str, Tuple[int, ast.FunctionDef]]:
    """Extract function definitions from source code.

    Returns dict mapping function name to (line_number, FunctionDef node).
    """
    functions = {}
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions[node.name] = (node.lineno, node)
    except SyntaxError:
        pass
    return functions


def _has_asserts(func_node: ast.FunctionDef) -> bool:
    """Check if a function has any assert statements."""
    for node in ast.walk(func_node):
        if isinstance(node, ast.Assert):
            return True
        # Also check for self.assert* method calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr.startswith('assert'):
                    return True
    return False


def _is_empty_body(func_node: ast.FunctionDef) -> bool:
    """Check if a function has an empty body (only pass, ..., or docstring)."""
    # Filter out docstring and ellipsis
    body = func_node.body

    # Remove docstring if present
    if body and isinstance(body[0], ast.Expr):
        if isinstance(body[0].value, ast.Constant):
            # Check if it's a string (docstring)
            if isinstance(body[0].value.value, str):
                body = body[1:]

    # Check if remaining body is empty or only contains pass/Ellipsis
    if not body:
        return True

    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr):
            if isinstance(stmt.value, ast.Constant) and stmt.value.value is ...:
                continue
            if isinstance(stmt.value, ast.Ellipsis):
                continue
        return False

    return True


def scan_markers(src_dirs: List[str], test_dirs: List[str]) -> Dict[str, List[MarkerLocation]]:
    """Scan source and test directories for AC markers.

    Returns a structure mapping AC -> list of (file, funcname, line) for implements and covers.
    """
    markers_by_ac = {}

    # Scan source files for implements markers
    for src_dir in src_dirs:
        for py_file in Path(src_dir).rglob('*.py'):
            try:
                source = py_file.read_text()
                comments = _tokenize_comments(source)
                functions = _extract_functions(source, str(py_file))

                for func_name, (line_num, func_node) in functions.items():
                    # Check for marker on line above or same line
                    for check_line in [line_num - 1, line_num]:
                        if check_line in comments:
                            marker_result = _parse_marker(comments[check_line])
                            if marker_result:
                                marker_type, ac_id = marker_result
                                if marker_type == 'implements':
                                    if ac_id not in markers_by_ac:
                                        markers_by_ac[ac_id] = []
                                    markers_by_ac[ac_id].append(
                                        MarkerLocation(
                                            file=str(py_file),
                                            funcname=func_name,
                                            line=line_num,
                                            ac_id=ac_id,
                                            marker_type=marker_type
                                        )
                                    )
            except Exception:
                pass

    # Scan test files for covers markers
    for test_dir in test_dirs:
        for py_file in Path(test_dir).rglob('*.py'):
            try:
                source = py_file.read_text()
                comments = _tokenize_comments(source)
                functions = _extract_functions(source, str(py_file))

                for func_name, (line_num, func_node) in functions.items():
                    # Check for marker on line above or same line
                    for check_line in [line_num - 1, line_num]:
                        if check_line in comments:
                            marker_result = _parse_marker(comments[check_line])
                            if marker_result:
                                marker_type, ac_id = marker_result
                                if marker_type == 'covers':
                                    if ac_id not in markers_by_ac:
                                        markers_by_ac[ac_id] = []
                                    markers_by_ac[ac_id].append(
                                        MarkerLocation(
                                            file=str(py_file),
                                            funcname=func_name,
                                            line=line_num,
                                            ac_id=ac_id,
                                            marker_type=marker_type
                                        )
                                    )
            except Exception:
                pass

    return markers_by_ac


def check(ac_ids: Set[str], src_paths: List[str], test_paths: List[str]) -> List[Dict]:
    """Check for AC marker violations.

    Returns a list of findings, each a dict with 'rule', 'file', 'line', 'message'.
    """
    findings = []

    # First, collect all implemented and covered ACs
    implemented_acs = {}  # AC id -> list of (file, func_name, line, func_node)
    covered_acs = {}      # AC id -> list of (file, func_name, line, func_node)

    # Scan source files for implementations
    for src_path in src_paths:
        try:
            source = Path(src_path).read_text()
            comments = _tokenize_comments(source)
            functions = _extract_functions(source, src_path)

            for func_name, (line_num, func_node) in functions.items():
                # Check for marker on line above or same line
                for check_line in [line_num - 1, line_num]:
                    if check_line in comments:
                        marker_result = _parse_marker(comments[check_line])
                        if marker_result:
                            marker_type, ac_id = marker_result
                            if marker_type == 'implements':
                                if ac_id not in implemented_acs:
                                    implemented_acs[ac_id] = []
                                implemented_acs[ac_id].append((src_path, func_name, line_num, func_node))
        except Exception:
            pass

    # Scan test files for covers markers
    for test_path in test_paths:
        try:
            source = Path(test_path).read_text()
            comments = _tokenize_comments(source)
            functions = _extract_functions(source, test_path)

            for func_name, (line_num, func_node) in functions.items():
                # Only check functions that start with test_
                if not func_name.startswith('test_'):
                    continue

                # Check for marker on line above or same line
                for check_line in [line_num - 1, line_num]:
                    if check_line in comments:
                        marker_result = _parse_marker(comments[check_line])
                        if marker_result:
                            marker_type, ac_id = marker_result
                            if marker_type == 'covers':
                                if ac_id not in covered_acs:
                                    covered_acs[ac_id] = []
                                covered_acs[ac_id].append((test_path, func_name, line_num, func_node))
        except Exception:
            pass

    # Now check for violations

    # SG201: Check if there are ACs that are tested but not implemented
    for ac_id, test_list in covered_acs.items():
        if ac_id not in implemented_acs:
            # AC is tested but not implemented - SG201
            for test_path, func_name, line_num, func_node in test_list:
                findings.append({
                    'rule': 'SG201',
                    'file': test_path,
                    'line': line_num,
                    'message': f"Test covers {ac_id} but no implementation found with '# implements: {ac_id}' marker"
                })

    # SG202: Check if there are ACs that are implemented but not tested
    for ac_id, impl_list in implemented_acs.items():
        if ac_id not in covered_acs:
            # AC is implemented but not tested - SG202
            for src_path, func_name, line_num, func_node in impl_list:
                findings.append({
                    'rule': 'SG202',
                    'file': src_path,
                    'line': line_num,
                    'message': f"Implementation of {ac_id} found but no test with '# covers: {ac_id}' marker"
                })

    # SG203: Check if markers reference known AC ids
    for ac_id in list(implemented_acs.keys()) + list(covered_acs.keys()):
        if ac_id not in ac_ids:
            # Check implemented ACs
            if ac_id in implemented_acs:
                for src_path, func_name, line_num, func_node in implemented_acs[ac_id]:
                    findings.append({
                        'rule': 'SG203',
                        'file': src_path,
                        'line': line_num,
                        'message': f"Marker references unknown AC id: {ac_id}"
                    })
            # Check covered ACs
            if ac_id in covered_acs:
                for test_path, func_name, line_num, func_node in covered_acs[ac_id]:
                    findings.append({
                        'rule': 'SG203',
                        'file': test_path,
                        'line': line_num,
                        'message': f"Marker references unknown AC id: {ac_id}"
                    })

    # SG204: Check if test functions with covers marker have asserts
    for ac_id, test_list in covered_acs.items():
        for test_path, func_name, line_num, func_node in test_list:
            if not _has_asserts(func_node):
                findings.append({
                    'rule': 'SG204',
                    'file': test_path,
                    'line': line_num,
                    'message': f"Test '{func_name}' with '# covers: {ac_id}' has no assert statements"
                })

    # SG205: Check if implements functions have empty bodies
    for ac_id, impl_list in implemented_acs.items():
        for src_path, func_name, line_num, func_node in impl_list:
            if _is_empty_body(func_node):
                findings.append({
                    'rule': 'SG205',
                    'file': src_path,
                    'line': line_num,
                    'message': f"Function '{func_name}' with '# implements: {ac_id}' has empty body"
                })

    return findings


def get_marker_map(src_dirs: List[str], test_dirs: List[str]) -> Dict[str, List[MarkerLocation]]:
    """Get the marker map for AC -> impl -> test trace.

    This is an alias for scan_markers for clarity.
    """
    return scan_markers(src_dirs, test_dirs)
