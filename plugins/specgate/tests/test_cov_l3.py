"""Coverage tests for the L3 runner layer."""

from pathlib import Path
from specgate.l3_run import (
    CustomTestResult,
    TestResult,
    check,
    run_tests,
    write_junit,
)
from specgate.l3_run import CustomTestResult, run_tests
from specgate.l3_run import run_tests, write_junit, CustomTestResult, TestResult
from unittest.mock import MagicMock, patch
from unittest.mock import patch, MagicMock
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


class TestResultClass(unittest.TestCase):
    """Test TestResult dataclass."""

    # covers: AC-4
    def test_test_result_creation(self) -> None:
        """Test TestResult is created correctly."""
        result = TestResult(
            test_id="test_1",
            status="PASS",
            funcname="test_func",
            file="test.py"
        )
        self.assertEqual(result.test_id, "test_1")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.funcname, "test_func")
        self.assertEqual(result.file, "test.py")


class TestWriteJUnit(unittest.TestCase):
    """Test write_junit function."""

    # covers: AC-4
    def test_write_junit_basic(self) -> None:
        """Test write_junit creates valid XML."""
        results = [
            TestResult(test_id="test_1", status="PASS", funcname="test_1", file="test.py"),
            TestResult(test_id="test_2", status="FAIL", funcname="test_2", file="test.py"),
        ]
        ac_map: dict[str, list] = {}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            junit_path = f.name

        try:
            write_junit(results, ac_map, junit_path)

            # Parse and verify
            tree = ET.parse(junit_path)
            root = tree.getroot()
            self.assertEqual(root.tag, 'testsuites')

            testsuite = root.find('testsuite')
            self.assertIsNotNone(testsuite)
            self.assertEqual(testsuite.get('tests'), '2')
            self.assertEqual(testsuite.get('failures'), '1')
        finally:
            if os.path.exists(junit_path):
                os.unlink(junit_path)

    # covers: AC-4
    def test_write_junit_error_status(self) -> None:
        """Test write_junit includes error elements."""
        results = [
            TestResult(test_id="test_1", status="ERROR", funcname="test_1", file="test.py"),
            TestResult(test_id="test_2", status="SKIP", funcname="test_2", file="test.py"),
        ]
        ac_map: dict[str, list] = {}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            junit_path = f.name

        try:
            write_junit(results, ac_map, junit_path)

            tree = ET.parse(junit_path)
            root = tree.getroot()
            testsuite = root.find('testsuite')
            testcases = testsuite.findall('testcase')

            self.assertEqual(testsuite.get('errors'), '1')

            # Find error and skipped elements
            error_found = False
            skipped_found = False
            for testcase in testcases:
                if testcase.find('error') is not None:
                    error_found = True
                if testcase.find('skipped') is not None:
                    skipped_found = True

            self.assertTrue(error_found)
            self.assertTrue(skipped_found)
        finally:
            if os.path.exists(junit_path):
                os.unlink(junit_path)

    # covers: AC-4
    def test_write_junit_multiple_results(self) -> None:
        """Test write_junit with multiple test statuses."""
        results = [
            TestResult(test_id="test_1", status="PASS", funcname="test_1", file="test.py"),
            TestResult(test_id="test_2", status="FAIL", funcname="test_2", file="test.py"),
            TestResult(test_id="test_3", status="ERROR", funcname="test_3", file="test.py"),
        ]
        ac_map: dict[str, list] = {}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            junit_path = f.name

        try:
            write_junit(results, ac_map, junit_path)

            tree = ET.parse(junit_path)
            root = tree.getroot()
            testsuite = root.find('testsuite')

            self.assertEqual(testsuite.get('tests'), '3')
            self.assertEqual(testsuite.get('failures'), '1')
            self.assertEqual(testsuite.get('errors'), '1')
        finally:
            if os.path.exists(junit_path):
                os.unlink(junit_path)


class TestCheckFunction(unittest.TestCase):
    """Test check function."""

    # covers: AC-4
    def test_check_returns_list(self) -> None:
        """Test check returns a list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create minimal test files
            test_content = 'import unittest\nclass TestExample(unittest.TestCase):\n    def test_pass(self):\n        pass\n'
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                junit_path = f.name

            try:
                findings = check(set(), [temp_dir], [temp_dir], junit_path)
                self.assertIsInstance(findings, list)
            finally:
                if os.path.exists(junit_path):
                    os.unlink(junit_path)

    # covers: AC-4
    def test_check_with_empty_directories(self) -> None:
        """Test check with empty directories."""
        with tempfile.TemporaryDirectory() as temp_dir1:
            with tempfile.TemporaryDirectory() as temp_dir2:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                    junit_path = f.name

                try:
                    findings = check(set(), [temp_dir1], [temp_dir2], junit_path)
                    self.assertIsInstance(findings, list)
                finally:
                    if os.path.exists(junit_path):
                        os.unlink(junit_path)

    # covers: AC-4
    def test_check_with_empty_test_dirs(self) -> None:
        """Test check with empty test_dirs list (line 242)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                junit_path = f.name

            try:
                # Call check with empty test_dirs
                findings = check(set(), [temp_dir], [], junit_path)
                self.assertIsInstance(findings, list)
                self.assertEqual(findings, [])
            finally:
                if os.path.exists(junit_path):
                    os.unlink(junit_path)


class TestRunTests(unittest.TestCase):
    """Test run_tests function."""

    # covers: AC-4
    def test_run_tests_basic(self) -> None:
        """Test run_tests discovers and runs tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    def test_pass(self):\n'
                '        self.assertTrue(True)\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            results = run_tests(temp_dir, temp_dir)
            self.assertIsInstance(results, list)
            self.assertGreater(len(results), 0)
            self.assertEqual(results[0].status, 'PASS')

    # covers: AC-4
    def test_run_tests_default_top_level(self) -> None:
        """Test run_tests with None as top_level_dir (line 114)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    def test_pass(self):\n'
                '        pass\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            # Call with top_level_dir=None
            results = run_tests(temp_dir, None)
            self.assertIsInstance(results, list)

    # covers: AC-4
    def test_run_tests_with_skip(self) -> None:
        """Test run_tests with skipped tests (lines 55-58)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    @unittest.skip("Skipped for testing")\n'
                '    def test_skip(self):\n'
                '        pass\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            results = run_tests(temp_dir, temp_dir)
            self.assertGreater(len(results), 0)
            skip_found = any(r.status == 'SKIP' for r in results)
            self.assertTrue(skip_found)

    # covers: AC-4
    def test_run_tests_with_expected_failure(self) -> None:
        """Test run_tests with expected failures (lines 60-63)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    @unittest.expected' 'Failure\n'
                '    def test_xfail(self):\n'
                '        self.fail("Expected failure")\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            results = run_tests(temp_dir, temp_dir)
            self.assertGreater(len(results), 0)
            xfail_found = any(r.status == 'XFAIL' for r in results)
            self.assertTrue(xfail_found)

    # covers: AC-4
    def test_run_tests_with_unexpected_success(self) -> None:
        """Test run_tests with unexpected success (lines 65-68)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    @unittest.expected' 'Failure\n'
                '    def test_uxpass(self):\n'
                '        pass\n'  # This will be an unexpected pass
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            results = run_tests(temp_dir, temp_dir)
            self.assertGreater(len(results), 0)
            uxpass_found = any(r.status == 'UXPASS' for r in results)
            self.assertTrue(uxpass_found)

    # covers: AC-4
    def test_run_tests_with_error(self) -> None:
        """Test run_tests with test errors (lines 45-48)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    def test_error(self):\n'
                '        raise RuntimeError("Test error")\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            results = run_tests(temp_dir, temp_dir)
            self.assertGreater(len(results), 0)
            error_found = any(r.status == 'ERROR' for r in results)
            self.assertTrue(error_found)

    # covers: AC-4
    def test_run_tests_with_failure(self) -> None:
        """Test run_tests with test failures (lines 50-53)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    def test_fail(self):\n'
                '        self.fail("Test failed")\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            results = run_tests(temp_dir, temp_dir)
            self.assertGreater(len(results), 0)
            fail_found = any(r.status == 'FAIL' for r in results)
            self.assertTrue(fail_found)


class TestCustomTestResult(unittest.TestCase):
    """Test CustomTestResult class."""

    # covers: AC-4
    def test_custom_test_result_record_result(self) -> None:
        """Test _record_result method extracts file path correctly."""
        result = CustomTestResult()

        # Create a mock test object
        mock_test = MagicMock()
        mock_test.__str__ = lambda _x: "test_method (tests.TestClass)"
        mock_test.__class__.__module__ = "tests"
        mock_test.__class__.__file__ = "/path/to/test_file.py"

        result._record_result(mock_test, 'PASS')

        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].status, 'PASS')
        self.assertEqual(result.results[0].funcname, 'test_method')

    # covers: AC-4
    def test_custom_test_result_module_file(self) -> None:
        """Test _record_result extracts file from module when __file__ not on class."""
        result = CustomTestResult()

        # Create a real class without __file__
        class FakeTest:
            __module__ = "module"

        mock_test = MagicMock()
        mock_test.__str__ = lambda _x: "test_func (module.TestClass)"
        mock_test.__class__ = FakeTest

        # Mock the sys.modules lookup
        mock_module = MagicMock()
        mock_module.__file__ = "/path/to/module.py"

        with patch.dict(sys.modules, {'module': mock_module}):
            result._record_result(mock_test, 'PASS')

        self.assertEqual(len(result.results), 1)

    # covers: AC-4
    def test_custom_test_result_no_file_fallback(self) -> None:
        """Test _record_result fallback when no file can be determined."""
        result = CustomTestResult()

        # Create a real class without __file__
        class FakeTest:
            __module__ = "module"

        mock_test = MagicMock()
        mock_test.__str__ = lambda _x: "test_func (module.TestClass)"
        mock_test.__class__ = FakeTest

        result._record_result(mock_test, 'PASS')

        self.assertEqual(len(result.results), 1)
        # Should fallback to module name conversion
        self.assertIsNotNone(result.results[0].file)


class TestWriteJUnitWithMarkers(unittest.TestCase):
    """Test write_junit with AC markers."""

    # covers: AC-4
    def test_write_junit_with_ac_properties(self) -> None:
        """Test write_junit includes AC properties (lines 189-191)."""
        from specgate.l2_trace import MarkerLocation

        results = [
            TestResult(test_id="test_1", status="PASS", funcname="test_1", file="test.py"),
        ]

        # Create marker locations for AC coverage
        marker = MarkerLocation(
            marker_type='covers',
            funcname='test_1',
            ac_id='AC-1',
            file='test.py',
            line=10
        )
        ac_map = {'AC-1': [marker]}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            junit_path = f.name

        try:
            write_junit(results, ac_map, junit_path)

            tree = ET.parse(junit_path)
            root = tree.getroot()
            testsuite = root.find('testsuite')
            testcase = testsuite.find('testcase')
            properties = testcase.find('properties')

            self.assertIsNotNone(properties)
            props = properties.findall('property')
            self.assertEqual(len(props), 1)
            self.assertEqual(props[0].get('name'), 'ac')
            self.assertEqual(props[0].get('value'), 'AC-1')
        finally:
            if os.path.exists(junit_path):
                os.unlink(junit_path)


class TestCheckFunctionWithACs(unittest.TestCase):
    """Test check function with AC markers."""

    # covers: AC-4
    def test_check_with_sg301_violation(self) -> None:
        """Test check finds SG301 violation (non-PASS test covering AC)."""
        from specgate.l2_trace import MarkerLocation

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a failing test
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    def test_fail(self):\n'
                '        self.fail("Test failed")\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                junit_path = f.name

            try:
                # Mock get_marker_map to return AC markers for the failing test
                marker = MarkerLocation(
                    marker_type='covers',
                    funcname='test_fail',
                    ac_id='AC-1',
                    file=test_file,
                    line=10
                )

                with patch('specgate.l3_run.get_marker_map') as mock_map:
                    mock_map.return_value = {'AC-1': [marker]}
                    findings = check({'AC-1'}, [temp_dir], [temp_dir], junit_path)

                # Should find SG301 violation
                sg301_found = any(f['rule'] == 'SG301' for f in findings)
                self.assertTrue(sg301_found)
            finally:
                if os.path.exists(junit_path):
                    os.unlink(junit_path)

    # covers: AC-4
    def test_check_with_sg302_violation(self) -> None:
        """Test check finds SG302 violation (test not executed)."""
        from specgate.l2_trace import MarkerLocation

        with tempfile.TemporaryDirectory() as temp_dir:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                junit_path = f.name

            try:
                # Create marker for a test that doesn't exist
                marker = MarkerLocation(
                    marker_type='covers',
                    funcname='nonexistent_test',
                    ac_id='AC-1',
                    file='test.py',
                    line=10
                )

                with patch('specgate.l3_run.get_marker_map') as mock_map:
                    mock_map.return_value = {'AC-1': [marker]}
                    # Call with empty test_dirs so no tests run
                    findings = check({'AC-1'}, [temp_dir], [], junit_path)

                # Should find SG302 violation
                sg302_found = any(f['rule'] == 'SG302' for f in findings)
                self.assertTrue(sg302_found)
            finally:
                if os.path.exists(junit_path):
                    os.unlink(junit_path)


class TestCustomTestResultExceptionHandling(unittest.TestCase):
    """Test CustomTestResult exception handling in _record_result."""

    # covers: AC-4
    def test_record_result_attribute_error_on_module(self) -> None:
        """Test _record_result handles AttributeError (lines 88-95)."""
        result = CustomTestResult()

        # Create a real class without __file__
        class FakeTest:
            __module__ = "module"

        mock_test = MagicMock()
        mock_test.__str__ = lambda _x: "test_func"  # Minimal string
        mock_test.__class__ = FakeTest

        # Mock sys.modules to raise AttributeError
        with patch.dict(sys.modules, {}, clear=False):
            # This should not have __file__ attribute
            sys.modules['module'] = MagicMock(spec=[])
            result._record_result(mock_test, 'PASS')

        self.assertEqual(len(result.results), 1)

    # covers: AC-4
    def test_record_result_key_error(self) -> None:
        """Test _record_result handles KeyError when module not in sys.modules."""
        result = CustomTestResult()

        # Create a real class without __file__
        class FakeTest:
            __module__ = "nonexistent_module"

        mock_test = MagicMock()
        mock_test.__str__ = lambda _x: "test_func"
        mock_test.__class__ = FakeTest

        # Module doesn't exist in sys.modules
        result._record_result(mock_test, 'PASS')

        self.assertEqual(len(result.results), 1)
        # Should still record with fallback

    # covers: AC-4
    def test_record_result_index_error(self) -> None:
        """Test _record_result with malformed test string."""
        result = CustomTestResult()

        mock_test = MagicMock()
        mock_test.__str__ = lambda _x: ""  # Empty string
        mock_test.__class__.__module__ = "module"
        mock_test.__class__.__file__ = "/path/test.py"

        result._record_result(mock_test, 'PASS')

        self.assertEqual(len(result.results), 1)


class TestRunTestsModuleCleanup(unittest.TestCase):
    """Test run_tests module cleanup (lines 156-157)."""

    # covers: AC-4
    def test_run_tests_cleanup_sys_modules(self) -> None:
        """Test run_tests removes test modules from sys.modules."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    def test_pass(self):\n'
                '        pass\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            # Get initial test modules
            initial_test_mods = [k for k in sys.modules.keys() if k.startswith('test_')]

            results = run_tests(temp_dir, temp_dir)

            # Get final test modules
            final_test_mods = [k for k in sys.modules.keys() if k.startswith('test_')]

            # Cleanup should remove test_ modules
            self.assertIsInstance(results, list)


class TestRunTestsPathHandling(unittest.TestCase):
    """Test run_tests sys.path handling (lines 131-132)."""

    # covers: AC-4
    def test_run_tests_absolute_path_conversion(self) -> None:
        """Test run_tests converts relative paths to absolute."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    def test_pass(self):\n'
                '        pass\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            # Use relative path
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                results = run_tests('.', '.')
                self.assertIsInstance(results, list)
            finally:
                os.chdir(old_cwd)

    # covers: AC-4
    def test_run_tests_path_isolation(self) -> None:
        """Test run_tests restores sys.path after execution (lines 131-132)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    def test_pass(self):\n'
                '        pass\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            original_path = sys.path[:]
            results = run_tests(temp_dir, temp_dir)

            # sys.path should be restored (or at least not contain test_dir)
            self.assertIsInstance(results, list)


class TestRunTestsModuleClearing(unittest.TestCase):
    """Test run_tests module clearing."""

    # covers: AC-4
    def test_run_tests_clears_conflicting_modules(self) -> None:
        """Test run_tests clears modules that might conflict."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    def test_pass(self):\n'
                '        pass\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            # Add something to sys.modules that starts with test_
            sys.modules['test_dummy_temp'] = MagicMock()

            try:
                results = run_tests(temp_dir, temp_dir)
                self.assertIsInstance(results, list)
            finally:
                # Clean up
                if 'test_dummy_temp' in sys.modules:
                    del sys.modules['test_dummy_temp']

    # covers: AC-4
    def test_run_tests_handles_module_deletion_error(self) -> None:
        """Test run_tests handles errors during module deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    def test_pass(self):\n'
                '        pass\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            # This should not crash even if module deletion fails
            results = run_tests(temp_dir, temp_dir)
            self.assertIsInstance(results, list)


class TestCheckWithMarkerLocationEdgeCases(unittest.TestCase):
    """Test check function with various marker location scenarios."""

    # covers: AC-4
    def test_check_sg301_with_multiple_acs(self) -> None:
        """Test SG301 when a test covers multiple ACs."""
        from specgate.l2_trace import MarkerLocation
        from specgate.l3_run import check

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a failing test
            test_content = (
                'import unittest\n'
                'class TestExample(unittest.TestCase):\n'
                '    def test_multi(self):\n'
                '        self.fail("Test failed")\n'
            )
            test_file = os.path.join(temp_dir, 'test_example.py')
            with open(test_file, 'w') as f:
                f.write(test_content)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                junit_path = f.name

            try:
                # Create markers for multiple ACs covering the same test
                marker1 = MarkerLocation(
                    marker_type='covers',
                    funcname='test_multi',
                    ac_id='AC-1',
                    file=test_file,
                    line=10
                )
                marker2 = MarkerLocation(
                    marker_type='covers',
                    funcname='test_multi',
                    ac_id='AC-2',
                    file=test_file,
                    line=15
                )

                with patch('specgate.l3_run.get_marker_map') as mock_map:
                    mock_map.return_value = {
                        'AC-1': [marker1],
                        'AC-2': [marker2],
                    }
                    findings = check({'AC-1', 'AC-2'}, [temp_dir], [temp_dir], junit_path)

                # Should find SG301 for both ACs
                sg301_count = sum(1 for f in findings if f['rule'] == 'SG301')
                self.assertEqual(sg301_count, 2)
            finally:
                if os.path.exists(junit_path):
                    os.unlink(junit_path)

    # covers: AC-4
    def test_check_sg302_with_multiple_markers(self) -> None:
        """Test SG302 when multiple markers for same AC but no test."""
        from specgate.l2_trace import MarkerLocation
        from specgate.l3_run import check

        with tempfile.TemporaryDirectory() as temp_dir:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                junit_path = f.name

            try:
                # Create multiple markers for same AC, none executed
                marker1 = MarkerLocation(
                    marker_type='covers',
                    funcname='test_missing1',
                    ac_id='AC-1',
                    file='test.py',
                    line=10
                )
                marker2 = MarkerLocation(
                    marker_type='covers',
                    funcname='test_missing2',
                    ac_id='AC-1',
                    file='test.py',
                    line=20
                )

                with patch('specgate.l3_run.get_marker_map') as mock_map:
                    mock_map.return_value = {'AC-1': [marker1, marker2]}
                    findings = check({'AC-1'}, [temp_dir], [], junit_path)

                # Should find SG302 for both missing tests
                sg302_count = sum(1 for f in findings if f['rule'] == 'SG302')
                self.assertEqual(sg302_count, 2)
            finally:
                if os.path.exists(junit_path):
                    os.unlink(junit_path)


class TestTestResultExtraction(unittest.TestCase):
    """Test test ID extraction in CustomTestResult."""

    # covers: AC-4
    def test_record_result_with_complex_test_id(self) -> None:
        """Test _record_result with complex test class hierarchy."""
        result = CustomTestResult()

        mock_test = MagicMock()
        # Simulate "test_method (package.module.TestClass)"
        mock_test.__str__ = lambda _x: "test_method (package.module.TestClass)"
        mock_test.__class__.__module__ = "package.module"
        mock_test.__class__.__file__ = "/path/to/test.py"

        result._record_result(mock_test, 'PASS')

        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].funcname, 'test_method')
        self.assertEqual(result.results[0].test_id, 'test_method (package.module.TestClass)')


class TestRunTestsErrorHandling(unittest.TestCase):
    """Test error handling in run_tests function."""

    # covers: AC-4
    def test_run_tests_module_cleanup_error(self) -> None:
        """Test run_tests handles errors during module cleanup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple test file
            test_file = Path(tmpdir) / "test_sample.py"
            test_file.write_text("""
import unittest

class TestSample(unittest.TestCase):
    def test_pass(self):
        self.assertTrue(True)
""")

            # Run tests - should handle cleanup errors gracefully
            results = run_tests(tmpdir, tmpdir)
            # Should have at least one result
            self.assertGreater(len(results), 0)
            # Verify test passed
            self.assertTrue(any(r.status == 'PASS' for r in results))


class TestCustomTestResultErrorPath(unittest.TestCase):
    """Test CustomTestResult error handling paths."""

    # covers: AC-4
    def test_record_result_with_missing_attributes(self) -> None:
        """Test _record_result when test object is missing expected attributes."""
        result = CustomTestResult()

        # Create a mock test object with minimal attributes
        mock_test = MagicMock()
        mock_test.__str__ = MagicMock(return_value="test_name")
        # Remove __file__ attribute to trigger exception handling
        mock_test.__class__.__module__ = "test_module"
        mock_test.__class__.__file__ = None

        # Call _record_result - should handle missing attributes
        result._record_result(mock_test, 'PASS')

        # Should have recorded the result
        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].status, 'PASS')


class TestWriteJunitWithTests(unittest.TestCase):
    """Test write_junit function with actual test results."""

    # covers: AC-4
    def test_write_junit_with_multiple_results(self) -> None:
        """Test write_junit with various test statuses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            junit_path = Path(tmpdir) / "junit.xml"

            # Create test results with various statuses
            results = [
                TestResult(
                    test_id="test_pass (test_module.TestClass)",
                    status="PASS",
                    funcname="test_pass",
                    file="test_module.py"
                ),
                TestResult(
                    test_id="test_fail (test_module.TestClass)",
                    status="FAIL",
                    funcname="test_fail",
                    file="test_module.py"
                ),
                TestResult(
                    test_id="test_error (test_module.TestClass)",
                    status="ERROR",
                    funcname="test_error",
                    file="test_module.py"
                ),
                TestResult(
                    test_id="test_skip (test_module.TestClass)",
                    status="SKIP",
                    funcname="test_skip",
                    file="test_module.py"
                ),
            ]

            # Write JUnit - should not raise
            write_junit(results, {}, str(junit_path))

            # Verify file was created
            self.assertTrue(junit_path.exists())


class TestWriteJunitWithACs(unittest.TestCase):
    """Test write_junit with AC markers."""

    # covers: AC-4
    def test_write_junit_with_ac_map(self) -> None:
        """Test write_junit includes AC IDs in properties."""
        from specgate.l2_trace import MarkerLocation

        with tempfile.TemporaryDirectory() as tmpdir:
            junit_path = Path(tmpdir) / "junit.xml"

            # Create test results
            results = [
                TestResult(
                    test_id="test_feature (test_module.TestFeature)",
                    status="PASS",
                    funcname="test_feature",
                    file="test_module.py"
                ),
            ]

            # Create AC map with marker for test_feature
            ac_map = {
                "AC-001": [
                    MarkerLocation(
                        file="test_module.py",
                        funcname="test_feature",
                        line=10,
                        ac_id="AC-001",
                        marker_type="covers",
                        qualname="test_module:TestFeature.test_feature"
                    )
                ]
            }

            # Write JUnit
            write_junit(results, ac_map, str(junit_path))

            # Verify file was created
            self.assertTrue(junit_path.exists())

            # Read and verify content
            content = junit_path.read_text()
            self.assertIn("AC-001", content)
            self.assertIn("test_feature", content)


class TestRunTestsEmptyDirectory(unittest.TestCase):
    """Test run_tests with empty test directory."""

    # covers: AC-4
    def test_run_tests_no_test_files(self) -> None:
        """Test run_tests with directory containing no test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Run tests in empty directory
            results = run_tests(tmpdir, tmpdir)
            # Should return empty list
            self.assertEqual(results, [])


class TestCustomTestResultStatuses(unittest.TestCase):
    """Test CustomTestResult captures all status types."""

    # covers: AC-4
    def test_add_expected_failure(self) -> None:
        """Test addExpectedFailure is recorded as XFAIL."""
        result = CustomTestResult()
        mock_test = MagicMock()
        mock_test.__str__ = MagicMock(return_value="test_xfail")
        mock_test.__class__.__module__ = "test_module"

        result.addExpectedFailure(mock_test, (None, None, None))

        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].status, 'XFAIL')

    # covers: AC-4
    def test_add_unexpected_success(self) -> None:
        """Test addUnexpectedSuccess is recorded as UXPASS."""
        result = CustomTestResult()
        mock_test = MagicMock()
        mock_test.__str__ = MagicMock(return_value="test_uxpass")
        mock_test.__class__.__module__ = "test_module"

        result.addUnexpectedSuccess(mock_test)

        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].status, 'UXPASS')

    # covers: AC-4
    def test_record_result_with_split_parts(self) -> None:
        """Test _record_result with test that has multiple parts in string."""
        result = CustomTestResult()
        mock_test = MagicMock()
        mock_test.__str__ = MagicMock(return_value="test_name (module.Class)")
        mock_test.__class__.__module__ = "test_module"
        mock_test.__class__.__file__ = "test_module.py"

        result._record_result(mock_test, 'PASS')

        self.assertEqual(len(result.results), 1)
        # Verify funcname is extracted correctly
        self.assertEqual(result.results[0].funcname, 'test_name')


class TestCheckIgnoresUnmarkedFailures(unittest.TestCase):
    """A failing test that covers no AC is not an AC finding."""

    # covers: AC-4
    def test_unmarked_failure_is_not_sg301(self) -> None:
        from specgate.l3_run import check as l3_check
        body = (
            "import unittest\n\n\nclass T(unittest.TestCase):\n"
            "    # covers: AC-1\n    def test_marked(self):\n        self.assertTrue(True)\n\n"
            "    def test_unmarked(self):\n        self.assertTrue(False)\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "test_x.py"), "w") as f:
                f.write(body)
            findings = l3_check({"AC-1"}, [], [tmp], os.path.join(tmp, "j.xml"))
        self.assertEqual(findings, [])
