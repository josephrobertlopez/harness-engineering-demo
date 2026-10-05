"""L3 layer: unittest runner with JUnit XML emission and AC tracing."""

import unittest
import xml.etree.ElementTree as ET
import sys
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from specgate.l2_trace import get_marker_map


@dataclass
class TestResult:
    """Represents a test result."""
    test_id: str
    status: str  # PASS, FAIL, ERROR, SKIP, XFAIL, UXPASS
    funcname: str
    file: str


class CustomTestResult(unittest.TestResult):
    """Custom test result that captures skips, expectedFailure, and unexpectedSuccess."""

    def __init__(self, stream=None, descriptions=None, verbosity=None):
        super().__init__(stream, descriptions, verbosity)
        self.results: List[TestResult] = []

    def startTest(self, test):
        """Record the test that is starting."""
        super().startTest(test)
        self._current_test = test

    def addSuccess(self, test):
        """Handle test success."""
        super().addSuccess(test)
        self._record_result(test, 'PASS')

    def addError(self, test, err):
        """Handle test error."""
        super().addError(test, err)
        self._record_result(test, 'ERROR')

    def addFailure(self, test, err):
        """Handle test failure."""
        super().addFailure(test, err)
        self._record_result(test, 'FAIL')

    def addSkip(self, test, reason):
        """Handle test skip."""
        super().addSkip(test, reason)
        self._record_result(test, 'SKIP')

    def addExpectedFailure(self, test, err):
        """Handle expected failure."""
        super().addExpectedFailure(test, err)
        self._record_result(test, 'XFAIL')

    def addUnexpectedSuccess(self, test):
        """Handle unexpected success."""
        super().addUnexpectedSuccess(test)
        self._record_result(test, 'UXPASS')

    def _record_result(self, test, status):
        """Record a test result."""
        # Extract test ID from test object
        test_id = str(test)
        # Parse test_id format: "test_name (module.ClassName)"
        parts = test_id.split(' ')
        funcname = parts[0] if parts else test_id

        # Get the file path from the test method
        try:
            test_method = getattr(test, test.id().split('.')[-1])
            file_path = test.__class__.__module__.replace('.', os.sep) + '.py'
            # Try to get the actual file
            if hasattr(test.__class__, '__file__'):
                file_path = test.__class__.__file__
            else:
                # Use the module's __file__
                try:
                    module = sys.modules[test.__class__.__module__]
                    if hasattr(module, '__file__'):
                        file_path = module.__file__
                except (KeyError, AttributeError):
                    pass
        except (AttributeError, IndexError):
            file_path = test.__class__.__module__

        self.results.append(TestResult(
            test_id=test_id,
            status=status,
            funcname=funcname,
            file=file_path
        ))


def run_tests(test_dir: str, top_level_dir: Optional[str] = None) -> List[TestResult]:
    """Run unittest tests from a directory.

    Args:
        test_dir: Directory to search for tests
        top_level_dir: Top-level directory for test discovery (defaults to test_dir)

    Returns:
        List of TestResult objects with test IDs, statuses, funcnames, and files
    """
    if top_level_dir is None:
        top_level_dir = test_dir

    # Convert to absolute path
    test_dir_abs = os.path.abspath(test_dir)
    top_level_dir_abs = os.path.abspath(top_level_dir)

    # Save the current sys.path
    original_path = sys.path[:]

    try:
        # Clear out modules that might conflict
        # Get the directory name to use as a module prefix
        dir_name = os.path.basename(test_dir_abs)
        modules_to_remove = [key for key in list(sys.modules.keys())
                            if key.startswith('test_') or key == dir_name or 'src' in key]
        for mod in modules_to_remove:
            try:
                del sys.modules[mod]
            except (KeyError, RuntimeError):
                pass

        # Clear sys.path of any entries that might conflict
        sys.path = [p for p in sys.path if test_dir_abs not in p or p == test_dir_abs]

        # Add test_dir to sys.path so tests can be imported
        sys.path.insert(0, test_dir_abs)

        loader = unittest.TestLoader()
        suite = loader.discover(test_dir_abs, pattern='test*.py', top_level_dir=test_dir_abs)

        result = CustomTestResult()
        suite.run(result)

        return result.results
    finally:
        # Restore sys.path
        sys.path[:] = original_path
        # Clear modules added during test discovery
        modules_to_remove = [key for key in list(sys.modules.keys())
                            if key.startswith('test_')]
        for mod in modules_to_remove:
            try:
                del sys.modules[mod]
            except (KeyError, RuntimeError):
                pass


def write_junit(results: List[TestResult], ac_map: Dict[str, List], path: str) -> None:
    """Write JUnit XML file with AC properties.

    Args:
        results: List of TestResult objects
        ac_map: Mapping from AC ID to list of MarkerLocation objects
        path: Path to write JUnit XML to
    """
    # Create root testsuites element
    testsuites = ET.Element('testsuites')

    # Create a single testsuite element
    testsuite = ET.SubElement(testsuites, 'testsuite')
    testsuite.set('name', 'all')
    testsuite.set('tests', str(len(results)))

    # Count failures and errors
    failures = sum(1 for r in results if r.status == 'FAIL')
    errors = sum(1 for r in results if r.status == 'ERROR')
    testsuite.set('failures', str(failures))
    testsuite.set('errors', str(errors))

    # Build a map from funcname to AC IDs
    funcname_to_acs: Dict[str, List[str]] = {}
    for ac_id, markers in ac_map.items():
        for marker in markers:
            if marker.marker_type == 'covers':
                if marker.funcname not in funcname_to_acs:
                    funcname_to_acs[marker.funcname] = []
                funcname_to_acs[marker.funcname].append(ac_id)

    # Add testcase elements
    for result in results:
        testcase = ET.SubElement(testsuite, 'testcase')
        testcase.set('name', result.funcname)
        testcase.set('classname', result.file)

        # Add AC properties for this test (sorted, deterministic)
        if result.funcname in funcname_to_acs:
            properties = ET.SubElement(testcase, 'properties')
            for ac_id in sorted(funcname_to_acs[result.funcname]):
                prop = ET.SubElement(properties, 'property')
                prop.set('name', 'ac')
                prop.set('value', ac_id)

        # Add status elements
        if result.status == 'FAIL':
            ET.SubElement(testcase, 'failure')
        elif result.status == 'ERROR':
            ET.SubElement(testcase, 'error')
        elif result.status == 'SKIP':
            ET.SubElement(testcase, 'skipped')

    # Write XML to file
    tree = ET.ElementTree(testsuites)
    tree.write(path, encoding='utf-8', xml_declaration=True)


def check(ac_ids: set, src_dirs: List[str], test_dirs: List[str], junit_path: str) -> List[Dict]:
    """Check for AC coverage violations and write JUnit XML.

    Args:
        ac_ids: Set of known AC IDs
        src_dirs: List of source directories to scan
        test_dirs: List of test directories to scan
        junit_path: Path to write JUnit XML to

    Returns:
        List of findings dicts with 'rule', 'file', 'line', 'message'
    """
    findings = []

    # Get the marker map
    ac_map = get_marker_map(src_dirs, test_dirs)

    # Run tests
    test_dir = test_dirs[0] if test_dirs else '.'
    results = run_tests(test_dir, test_dir)

    # Write JUnit XML
    write_junit(results, ac_map, junit_path)

    # Check for SG301: AC has a test with non-PASS status
    for result in results:
        if result.funcname in [m.funcname for markers in ac_map.values() for m in markers if m.marker_type == 'covers']:
            if result.status != 'PASS':
                # Find the AC IDs this test covers
                for ac_id, markers in ac_map.items():
                    for marker in markers:
                        if marker.marker_type == 'covers' and marker.funcname == result.funcname:
                            findings.append({
                                'rule': 'SG301',
                                'file': result.file,
                                'line': marker.line,
                                'message': f"AC {ac_id} has test {result.funcname} with status {result.status}"
                            })

    # Check for SG302: AC has no test that ran (marker found but test not executed)
    for ac_id, markers in ac_map.items():
        test_markers = [m for m in markers if m.marker_type == 'covers']
        if test_markers:
            # Check if any of these tests ran
            test_funcnames = [m.funcname for m in test_markers]
            ran = any(r.funcname in test_funcnames for r in results)
            if not ran:
                for marker in test_markers:
                    findings.append({
                        'rule': 'SG302',
                        'file': marker.file,
                        'line': marker.line,
                        'message': f"AC {ac_id} has no test that ran (marker found but test not executed)"
                    })

    return findings
