"""Coverage tests for the L2 marker-tracing layer."""

from pathlib import Path
from specgate.l2_trace import (
    scan_markers, check, MarkerLocation,
    _tokenize_comments, _parse_marker, _extract_functions,
    _has_asserts, _is_empty_body, get_marker_map
)
from specgate.l2_trace import (
    scan_markers, check, _parse_marker, _extract_functions, _is_empty_body
)
import tempfile
import unittest


class TestTokenizeComments(unittest.TestCase):
    """Test comment tokenization."""

    # covers: AC-3
    def test_tokenize_comments_simple(self) -> None:
        """Test extracting simple comments."""
        source = "x = 1  # implements: AC-1\n"
        comments = _tokenize_comments(source)
        self.assertEqual(comments[1], "implements: AC-1")

    # covers: AC-3
    def test_tokenize_comments_multiple(self) -> None:
        """Test extracting multiple comments."""
        source = "x = 1  # comment 1\ny = 2  # comment 2\n"
        comments = _tokenize_comments(source)
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[1], "comment 1")
        self.assertEqual(comments[2], "comment 2")

    # covers: AC-3
    def test_tokenize_comments_no_comments(self) -> None:
        """Test file with no comments."""
        source = "x = 1\ny = 2\n"
        comments = _tokenize_comments(source)
        self.assertEqual(len(comments), 0)

    # covers: AC-3
    def test_tokenize_comments_invalid_syntax(self) -> None:
        """Test tokenizing invalid Python syntax."""
        source = "def broken(\n"
        comments = _tokenize_comments(source)
        self.assertEqual(len(comments), 0)


class TestParseMarker(unittest.TestCase):
    """Test marker parsing."""

    # covers: AC-3
    def test_parse_marker_implements(self) -> None:
        """Test parsing implements marker."""
        marker_type, ac_id = _parse_marker("implements: AC-1")
        self.assertEqual(marker_type, "implements")
        self.assertEqual(ac_id, "AC-1")

    # covers: AC-3
    def test_parse_marker_covers(self) -> None:
        """Test parsing covers marker."""
        marker_type, ac_id = _parse_marker("covers: AC-2")
        self.assertEqual(marker_type, "covers")
        self.assertEqual(ac_id, "AC-2")

    # covers: AC-3
    def test_parse_marker_with_extra_text(self) -> None:
        """Test parsing marker with extra text."""
        marker_type, ac_id = _parse_marker("implements: AC-1 extra text")
        self.assertEqual(marker_type, "implements")
        self.assertEqual(ac_id, "AC-1")

    # covers: AC-3
    def test_parse_marker_invalid(self) -> None:
        """Test parsing invalid marker."""
        result = _parse_marker("invalid: AC-1")
        self.assertIsNone(result)

    # covers: AC-3
    def test_parse_marker_incomplete(self) -> None:
        """Test parsing incomplete marker."""
        result = _parse_marker("implements:")
        self.assertIsNone(result)

    # covers: AC-3
    def test_parse_marker_whitespace(self) -> None:
        """Test parsing marker with whitespace."""
        marker_type, ac_id = _parse_marker("  implements: AC-1  ")
        self.assertEqual(marker_type, "implements")
        self.assertEqual(ac_id, "AC-1")


class TestExtractFunctions(unittest.TestCase):
    """Test function extraction."""

    # covers: AC-3
    def test_extract_functions_simple(self) -> None:
        """Test extracting simple function."""
        source = "def foo():\n    pass\n"
        functions = _extract_functions(source, "test.py")
        self.assertIn("foo", functions)
        line, node, bare_name, qualname = functions["foo"]
        self.assertEqual(line, 1)
        self.assertEqual(bare_name, "foo")
        self.assertEqual(qualname, "test:foo")

    # covers: AC-3
    def test_extract_functions_class_method(self) -> None:
        """Test extracting method from class."""
        source = "class MyClass:\n    def method(self):\n        pass\n"
        functions = _extract_functions(source, "test.py")
        self.assertIn("MyClass.method", functions)
        line, node, bare_name, qualname = functions["MyClass.method"]
        self.assertEqual(bare_name, "method")
        self.assertEqual(qualname, "test:MyClass.method")

    # covers: AC-3
    def test_extract_functions_multiple_classes_same_method(self) -> None:
        """Test extracting methods with same name from different classes."""
        source = """
class ClassA:
    def test_method(self):
        pass

class ClassB:
    def test_method(self):
        pass
"""
        functions = _extract_functions(source, "test.py")
        self.assertIn("ClassA.test_method", functions)
        self.assertIn("ClassB.test_method", functions)

        line_a, node_a, bare_name_a, qualname_a = functions["ClassA.test_method"]
        line_b, node_b, bare_name_b, qualname_b = functions["ClassB.test_method"]

        # Each should have correct bare_name and qualname
        self.assertEqual(bare_name_a, "test_method")
        self.assertEqual(bare_name_b, "test_method")
        self.assertEqual(qualname_a, "test:ClassA.test_method")
        self.assertEqual(qualname_b, "test:ClassB.test_method")
        # Different line numbers
        self.assertNotEqual(line_a, line_b)

    # covers: AC-3
    def test_extract_functions_invalid_syntax(self) -> None:
        """Test extracting from invalid syntax."""
        source = "def broken(\n"
        functions = _extract_functions(source, "test.py")
        self.assertEqual(len(functions), 0)


class TestHasAsserts(unittest.TestCase):
    """Test assert detection."""

    # covers: AC-3
    def test_has_asserts_direct(self) -> None:
        """Test function with assert statement."""
        source = "def test():\n    assert x == 1\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertTrue(_has_asserts(node))

    # covers: AC-3
    def test_has_asserts_method(self) -> None:
        """Test function with self.assert* call."""
        source = "def test(self):\n    self.assertEqual(a, b)\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertTrue(_has_asserts(node))

    # covers: AC-3
    def test_has_asserts_none(self) -> None:
        """Test function with no asserts."""
        source = "def test():\n    x = 1\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertFalse(_has_asserts(node))


class TestIsEmptyBody(unittest.TestCase):
    """Test empty body detection."""

    # covers: AC-3
    def test_is_empty_body_pass(self) -> None:
        """Test function with only pass."""
        source = "def test():\n    pass\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertTrue(_is_empty_body(node))

    # covers: AC-3
    def test_is_empty_body_ellipsis(self) -> None:
        """Test function with only ellipsis."""
        source = "def test():\n    ...\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertTrue(_is_empty_body(node))

    # covers: AC-3
    def test_is_empty_body_docstring(self) -> None:
        """Test function with only docstring."""
        source = 'def test():\n    """Docstring"""\n'
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertTrue(_is_empty_body(node))

    # covers: AC-3
    def test_is_empty_body_docstring_pass(self) -> None:
        """Test function with docstring and pass."""
        source = 'def test():\n    """Docstring"""\n    pass\n'
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertTrue(_is_empty_body(node))

    # covers: AC-3
    def test_is_empty_body_code(self) -> None:
        """Test function with actual code."""
        source = "def test():\n    x = 1\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertFalse(_is_empty_body(node))


class TestScanMarkers(unittest.TestCase):
    """Test marker scanning."""

    # covers: AC-3
    def test_scan_markers_implements(self) -> None:
        """Test scanning for implements markers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    pass\n")

            markers = scan_markers([tmpdir], [])
            self.assertIn("AC-1", markers)
            self.assertEqual(len(markers["AC-1"]), 1)
            self.assertEqual(markers["AC-1"][0].ac_id, "AC-1")
            self.assertEqual(markers["AC-1"][0].qualname, "src:foo")

    # covers: AC-3
    def test_scan_markers_covers(self) -> None:
        """Test scanning for covers markers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    pass\n")

            markers = scan_markers([], [tmpdir])
            self.assertIn("AC-1", markers)
            self.assertEqual(len(markers["AC-1"]), 1)

    # covers: AC-3
    def test_scan_markers_both(self) -> None:
        """Test scanning for both implements and covers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    pass\n")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    pass\n")

            markers = scan_markers([str(src_file.parent)], [str(test_file.parent)])
            self.assertIn("AC-1", markers)
            self.assertEqual(len(markers["AC-1"]), 2)

    # covers: AC-3
    def test_scan_markers_different_classes_same_method(self) -> None:
        """Test scanning with different classes having same method names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("""
class ServiceA:
    # implements: AC-1
    def execute(self):
        pass

class ServiceB:
    # implements: AC-2
    def execute(self):
        pass
""")

            markers = scan_markers([tmpdir], [])
            self.assertIn("AC-1", markers)
            self.assertIn("AC-2", markers)

            # Both should have their respective qualnames
            ac1_markers = markers["AC-1"]
            ac2_markers = markers["AC-2"]

            self.assertEqual(ac1_markers[0].qualname, "src:ServiceA.execute")
            self.assertEqual(ac2_markers[0].qualname, "src:ServiceB.execute")


class TestCheck(unittest.TestCase):
    """Test checking AC markers."""

    # covers: AC-3
    def test_check_all_covered(self) -> None:
        """Test check with all ACs covered and implemented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    x = 1\n")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    assert True\n")

            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            self.assertEqual(len(findings), 0)

    # covers: AC-3
    def test_check_unimplemented(self) -> None:
        """Test check with unimplemented AC."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    assert True\n")

            findings = check({'AC-1'}, [], [str(test_file)])
            sg201_findings = [f for f in findings if f['rule'] == 'SG201']
            self.assertGreater(len(sg201_findings), 0)

    # covers: AC-3
    def test_check_untested(self) -> None:
        """Test check with untested implementation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    x = 1\n")

            findings = check({'AC-1'}, [str(src_file)], [])
            sg202_findings = [f for f in findings if f['rule'] == 'SG202']
            self.assertGreater(len(sg202_findings), 0)

    # covers: AC-3
    def test_check_unknown_ac(self) -> None:
        """Test check with unknown AC ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-99\ndef foo():\n    x = 1\n")

            findings = check({'AC-1'}, [str(src_file)], [])
            sg203_findings = [f for f in findings if f['rule'] == 'SG203']
            self.assertGreater(len(sg203_findings), 0)

    # covers: AC-3
    def test_check_no_asserts(self) -> None:
        """Test check for test without asserts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    x = 1\n")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    x = 1\n")

            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            sg204_findings = [f for f in findings if f['rule'] == 'SG204']
            self.assertGreater(len(sg204_findings), 0)

    # covers: AC-3
    def test_check_empty_impl(self) -> None:
        """Test check for empty implementation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    pass\n")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    assert True\n")

            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            sg205_findings = [f for f in findings if f['rule'] == 'SG205']
            self.assertGreater(len(sg205_findings), 0)


class TestGetMarkerMap(unittest.TestCase):
    """Test get_marker_map function."""

    # covers: AC-3
    def test_get_marker_map(self) -> None:
        """Test that get_marker_map is an alias for scan_markers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    pass\n")

            # Call both and verify they return the same result
            result1 = scan_markers([tmpdir], [])
            result2 = get_marker_map([tmpdir], [])

            self.assertEqual(result1, result2)


class TestMultipleSameNameMethods(unittest.TestCase):
    """Test that methods with the same name in different classes are tracked separately."""

    # covers: AC-3
    def test_different_classes_same_method_with_different_markers(self) -> None:
        """Test two classes with same method name carrying different AC markers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("""
class Handler:
    # implements: AC-10
    def process(self):
        return True

class Factory:
    # implements: AC-20
    def process(self):
        return False
""")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("""
# covers: AC-10
def test_handler_process():
    assert True

# covers: AC-20
def test_factory_process():
    assert True
""")

            # Check that both ACs are tracked separately
            findings = check(
                {'AC-10', 'AC-20'},
                [str(src_file)],
                [str(test_file)]
            )

            # Should have no violations - both ACs are implemented and covered
            self.assertEqual(len(findings), 0)

            # Verify markers have correct qualnames
            markers = scan_markers([tmpdir], [tmpdir])
            self.assertIn("AC-10", markers)
            self.assertIn("AC-20", markers)

            # AC-10 should have Handler.process
            ac10_qualnames = [m.qualname for m in markers["AC-10"]]
            self.assertIn("src:Handler.process", ac10_qualnames)

            # AC-20 should have Factory.process
            ac20_qualnames = [m.qualname for m in markers["AC-20"]]
            self.assertIn("src:Factory.process", ac20_qualnames)


class TestEmptyFiles(unittest.TestCase):
    """Test handling of empty Python files."""

    # covers: AC-3
    def test_extract_functions_empty_file(self) -> None:
        """Test extracting functions from empty file."""
        source = ""
        functions = _extract_functions(source, "test.py")
        self.assertEqual(len(functions), 0)

    # covers: AC-3
    def test_tokenize_comments_empty_file(self) -> None:
        """Test tokenizing empty file."""
        source = ""
        comments = _tokenize_comments(source)
        self.assertEqual(len(comments), 0)


class TestCheckWithExceptionHandling(unittest.TestCase):
    """Test check function with exception handling."""

    # covers: AC-3
    def test_check_with_file_not_found(self) -> None:
        """Test check with non-existent files."""
        findings = check({'AC-1'}, ['/nonexistent/src.py'], ['/nonexistent/test.py'])
        # Completes without error; the only finding is that AC-1 has no markers.
        self.assertEqual([f['rule'] for f in findings], ['SG206'])


class TestMarkerLocationQualname(unittest.TestCase):
    """Test MarkerLocation with qualname field."""

    # covers: AC-3
    def test_marker_location_has_qualname(self) -> None:
        """Test that MarkerLocation instances have qualname."""
        marker = MarkerLocation(
            file="test.py",
            funcname="test_foo",
            line=10,
            ac_id="AC-1",
            marker_type="covers",
            qualname="test:test_foo"
        )
        self.assertEqual(marker.qualname, "test:test_foo")
        self.assertEqual(marker.funcname, "test_foo")

    # covers: AC-3
    def test_marker_location_default_qualname(self) -> None:
        """Test that MarkerLocation has default empty qualname."""
        marker = MarkerLocation(
            file="test.py",
            funcname="test_foo",
            line=10,
            ac_id="AC-1",
            marker_type="covers"
        )
        self.assertEqual(marker.qualname, "")


class TestComplexMarkerScenarios(unittest.TestCase):
    """Test complex marker scenarios."""

    # covers: AC-3
    def test_scan_markers_nested_classes(self) -> None:
        """Test scanning with deeply nested structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("""
class Outer:
    # implements: AC-1
    def method(self):
        return True

    class Inner:
        def inner_method(self):
            pass
""")

            # Should find the Outer.method implementation
            markers = scan_markers([tmpdir], [])
            self.assertIn("AC-1", markers)

    # covers: AC-3
    def test_check_all_violations_in_one_run(self) -> None:
        """Test check function detecting all violation types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # File 1: Implemented but not tested (SG202)
            src1 = Path(tmpdir) / "src1.py"
            src1.write_text("# implements: AC-1\ndef foo():\n    x = 1\n")

            # File 2: Tested but not implemented (SG201)
            test1 = Path(tmpdir) / "test1.py"
            test1.write_text("# covers: AC-2\ndef test_bar():\n    assert True\n")

            # File 3: References unknown AC (SG203)
            src2 = Path(tmpdir) / "src2.py"
            src2.write_text("# implements: AC-999\ndef baz():\n    pass\n")

            findings = check({'AC-1', 'AC-2'},
                           [str(src1), str(src2)],
                           [str(test1)])

            # Should find SG202 (untested), SG201 (uncovered), SG203 (unknown)
            rules = [f['rule'] for f in findings]
            self.assertIn('SG202', rules)  # AC-1 implemented but not tested
            self.assertIn('SG201', rules)  # AC-2 tested but not implemented
            self.assertIn('SG203', rules)  # AC-999 is unknown


class TestTokenizeCommentsBranchCoverage(unittest.TestCase):
    """Test branch coverage for _tokenize_comments."""

    # covers: AC-3
    def test_tokenize_comments_with_tokenize_error(self) -> None:
        """Test tokenizing with tokenize error (handles gracefully)."""
        source = "def broken(\n"  # Incomplete function
        comments = _tokenize_comments(source)
        # Should return empty dict on tokenize error
        self.assertEqual(len(comments), 0)


class TestParseMarkerBranchCoverage(unittest.TestCase):
    """Test branch coverage for _parse_marker."""

    # covers: AC-3
    def test_parse_marker_empty_string(self) -> None:
        """Test parsing empty string."""
        result = _parse_marker("")
        self.assertIsNone(result)

    # covers: AC-3
    def test_parse_marker_no_colon(self) -> None:
        """Test parsing marker without colon."""
        result = _parse_marker("implements without colon")
        self.assertIsNone(result)

    # covers: AC-3
    def test_parse_marker_implements_no_id(self) -> None:
        """Test parsing implements marker without AC ID."""
        result = _parse_marker("implements:")
        self.assertIsNone(result)

    # covers: AC-3
    def test_parse_marker_covers_with_id(self) -> None:
        """Test parsing covers marker with proper format."""
        marker_type, ac_id = _parse_marker("covers: AC-123")
        self.assertEqual(marker_type, "covers")
        self.assertEqual(ac_id, "AC-123")


class TestExtractFunctionsBranchCoverage(unittest.TestCase):
    """Test branch coverage for _extract_functions."""

    # covers: AC-3
    def test_extract_async_function(self) -> None:
        """Test extracting async function."""
        source = "async def async_func():\n    await something()\n"
        functions = _extract_functions(source, "test.py")
        # AsyncFunctionDef is not extracted (only FunctionDef)
        self.assertNotIn("async_func", functions)

    # covers: AC-3
    def test_extract_nested_functions(self) -> None:
        """Test extracting with nested functions (only top-level)."""
        source = """def outer():
    def inner():
        pass
    pass
"""
        functions = _extract_functions(source, "test.py")
        # Should only get outer, not inner (nested functions not extracted)
        self.assertIn("outer", functions)
        self.assertNotIn("inner", functions)

    # covers: AC-3
    def test_extract_multiple_methods_in_one_class(self) -> None:
        """Test extracting multiple methods in one class."""
        source = """class MyClass:
    def method1(self):
        pass
    def method2(self):
        pass
    def method3(self):
        pass
"""
        functions = _extract_functions(source, "test.py")
        self.assertIn("MyClass.method1", functions)
        self.assertIn("MyClass.method2", functions)
        self.assertIn("MyClass.method3", functions)


class TestHasAssertsBranchCoverage(unittest.TestCase):
    """Test branch coverage for _has_asserts."""

    # covers: AC-3
    def test_has_asserts_multiple_asserts(self) -> None:
        """Test function with multiple assert statements."""
        source = "def test():\n    assert x == 1\n    assert y == 2\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertTrue(_has_asserts(node))

    # covers: AC-3
    def test_has_asserts_nested_asserts(self) -> None:
        """Test function with nested assert (in if statement)."""
        source = "def test():\n    if x:\n        assert y == 1\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertTrue(_has_asserts(node))

    # covers: AC-3
    def test_has_asserts_with_different_methods(self) -> None:
        """Test function with different self.assert* methods."""
        source = "def test(self):\n    self.assertNotEqual(a, b)\n    self.assertTrue(c)\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertTrue(_has_asserts(node))


class TestIsEmptyBodyBranchCoverage(unittest.TestCase):
    """Test branch coverage for _is_empty_body."""

    # covers: AC-3
    def test_is_empty_body_only_pass_multiple(self) -> None:
        """Test function with multiple pass statements."""
        source = "def test():\n    pass\n    pass\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertTrue(_is_empty_body(node))

    # covers: AC-3
    def test_is_empty_body_docstring_and_ellipsis(self) -> None:
        """Test function with both docstring and ellipsis."""
        source = 'def test():\n    """Doc"""\n    ...\n'
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertTrue(_is_empty_body(node))

    # covers: AC-3
    def test_is_empty_body_ellipsis_constant(self) -> None:
        """Test function with Ellipsis as name reference (not empty)."""
        source = "def test():\n    Ellipsis\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        # Ellipsis as a name reference (not a constant) is not treated as empty
        # since _is_empty_body only recognizes ast.Constant with value=... or ast.Ellipsis
        self.assertFalse(_is_empty_body(node))

    # covers: AC-3
    def test_is_empty_body_ellipsis_with_pass(self) -> None:
        """Test function with both ellipsis literal and pass."""
        source = "def test():\n    ...\n    pass\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        # Both ellipsis and pass are treated as empty
        self.assertTrue(_is_empty_body(node))


class TestScanMarkersIntegration(unittest.TestCase):
    """Test scan_markers with various marker scenarios."""

    # covers: AC-3
    def test_scan_markers_multiline_comment(self) -> None:
        """Test scanning with multiline comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("""# implements: AC-1
def foo():
    # Another comment
    pass
""")
            markers = scan_markers([tmpdir], [])
            self.assertIn("AC-1", markers)
            self.assertEqual(len(markers["AC-1"]), 1)

    # covers: AC-3
    def test_scan_markers_marker_on_same_line(self) -> None:
        """Test scanning with marker on same line as function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("def foo():  # implements: AC-1\n    pass\n")
            markers = scan_markers([tmpdir], [])
            self.assertIn("AC-1", markers)

    # covers: AC-3
    def test_scan_markers_multiple_dirs(self) -> None:
        """Test scanning with multiple directories."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                src_file1 = Path(tmpdir1) / "src.py"
                src_file1.write_text("# implements: AC-1\ndef foo():\n    pass\n")
                src_file2 = Path(tmpdir2) / "src.py"
                src_file2.write_text("# implements: AC-2\ndef bar():\n    pass\n")

                markers = scan_markers([tmpdir1, tmpdir2], [])
                self.assertIn("AC-1", markers)
                self.assertIn("AC-2", markers)


class TestCheckRuleDetection(unittest.TestCase):
    """Test check function for all rule violations."""

    # covers: AC-3
    def test_check_sg201_covered_not_implemented(self) -> None:
        """Test SG201: test covers AC but no implementation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    assert True\n")

            findings = check({'AC-1'}, [], [str(test_file)])
            sg201_findings = [f for f in findings if f['rule'] == 'SG201']
            self.assertGreater(len(sg201_findings), 0)

    # covers: AC-3
    def test_check_sg202_implemented_not_tested(self) -> None:
        """Test SG202: implementation has AC but no test covers it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    x = 1\n")

            findings = check({'AC-1'}, [str(src_file)], [])
            sg202_findings = [f for f in findings if f['rule'] == 'SG202']
            self.assertGreater(len(sg202_findings), 0)

    # covers: AC-3
    def test_check_sg203_unknown_ac_in_implementation(self) -> None:
        """Test SG203: marker references unknown AC ID in implementation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-99\ndef foo():\n    x = 1\n")

            findings = check({'AC-1', 'AC-2'}, [str(src_file)], [])
            sg203_findings = [f for f in findings if f['rule'] == 'SG203']
            self.assertGreater(len(sg203_findings), 0)

    # covers: AC-3
    def test_check_sg203_unknown_ac_in_test(self) -> None:
        """Test SG203: marker references unknown AC ID in test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-99\ndef test_foo():\n    assert True\n")

            findings = check({'AC-1'}, [], [str(test_file)])
            sg203_findings = [f for f in findings if f['rule'] == 'SG203']
            self.assertGreater(len(sg203_findings), 0)

    # covers: AC-3
    def test_check_sg204_test_without_asserts(self) -> None:
        """Test SG204: test covers AC but has no asserts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    x = 1\n")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    x = 1\n")

            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            sg204_findings = [f for f in findings if f['rule'] == 'SG204']
            self.assertGreater(len(sg204_findings), 0)

    # covers: AC-3
    def test_check_sg205_empty_implementation(self) -> None:
        """Test SG205: implementation of AC has empty body."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    ...\n")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    assert True\n")

            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            sg205_findings = [f for f in findings if f['rule'] == 'SG205']
            self.assertGreater(len(sg205_findings), 0)


class TestGetMarkerMapAlias(unittest.TestCase):
    """Test get_marker_map as alias for scan_markers."""

    # covers: AC-3
    def test_get_marker_map_returns_same_as_scan_markers(self) -> None:
        """Test that get_marker_map returns same result as scan_markers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    pass\n")

            scan_result = scan_markers([tmpdir], [])
            map_result = get_marker_map([tmpdir], [])

            self.assertEqual(scan_result, map_result)


class TestParseMarkerBranches(unittest.TestCase):
    """Test branch coverage for _parse_marker edge cases."""

    # covers: AC-3
    def test_parse_marker_implements_empty_id(self) -> None:
        """Test parsing implements marker with empty ID after colon."""
        result = _parse_marker("implements:")
        self.assertIsNone(result)

    # covers: AC-3
    def test_parse_marker_covers_empty_id(self) -> None:
        """Test parsing covers marker with empty ID after colon."""
        result = _parse_marker("covers:")
        self.assertIsNone(result)

    # covers: AC-3
    def test_parse_marker_implements_with_trailing_text(self) -> None:
        """Test parsing implements marker with trailing text after ID."""
        marker_type, ac_id = _parse_marker("implements: AC-123 extra text")
        self.assertEqual(marker_type, "implements")
        self.assertEqual(ac_id, "AC-123")

    # covers: AC-3
    def test_parse_marker_covers_with_trailing_text(self) -> None:
        """Test parsing covers marker with trailing text after ID."""
        marker_type, ac_id = _parse_marker("covers: AC-456 extra text")
        self.assertEqual(marker_type, "covers")
        self.assertEqual(ac_id, "AC-456")


class TestIsEmptyBodyBranchCoverageD(unittest.TestCase):
    """Test branch coverage for _is_empty_body edge cases."""

    # covers: AC-3
    def test_is_empty_body_with_code_and_pass(self) -> None:
        """Test function with code followed by pass statement."""
        source = "def test():\n    x = 1\n    pass\n"
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertFalse(_is_empty_body(node))

    # covers: AC-3
    def test_is_empty_body_with_only_docstring(self) -> None:
        """Test function with only docstring (truly empty)."""
        source = 'def test():\n    """Only docstring"""\n'
        functions = _extract_functions(source, "test.py")
        node = functions["test"][1]
        self.assertTrue(_is_empty_body(node))


class TestScanMarkersNoMarkers(unittest.TestCase):
    """Test scan_markers when no markers are found."""

    # covers: AC-3
    def test_scan_markers_no_markers_in_files(self) -> None:
        """Test scan_markers with files that have no markers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("def foo():\n    x = 1\n")

            markers = scan_markers([tmpdir], [])
            self.assertEqual(len(markers), 0)

    # covers: AC-3
    def test_scan_markers_wrong_marker_type_in_src(self) -> None:
        """Test scan_markers with covers marker in source files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# covers: AC-1\ndef foo():\n    pass\n")

            # covers in src should be ignored
            markers = scan_markers([tmpdir], [])
            self.assertEqual(len(markers), 0)

    # covers: AC-3
    def test_scan_markers_wrong_marker_type_in_test(self) -> None:
        """Test scan_markers with implements marker in test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# implements: AC-1\ndef test_foo():\n    pass\n")

            # implements in test should be ignored
            markers = scan_markers([], [tmpdir])
            self.assertEqual(len(markers), 0)


class TestCheckRuleBranches(unittest.TestCase):
    """Test branch coverage in check function."""

    # covers: AC-3
    def test_check_no_violations(self) -> None:
        """Test check with properly matched implementations and tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    x = 1\n")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    assert True\n")

            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            # Should have no violations
            self.assertEqual(len(findings), 0)

    # covers: AC-3
    def test_check_non_test_function_in_test_file(self) -> None:
        """Test check ignores functions not starting with test_."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    x = 1\n")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef helper():\n    assert True\n")

            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            # Should find SG202 (implemented but not tested) since helper() is ignored
            sg202_findings = [f for f in findings if f['rule'] == 'SG202']
            self.assertGreater(len(sg202_findings), 0)

    # covers: AC-3
    def test_check_multiple_acs_mixed_coverage(self) -> None:
        """Test check with multiple ACs with mixed coverage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("""# implements: AC-1
def foo():
    x = 1

# implements: AC-2
def bar():
    y = 2
""")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    assert True\n")

            findings = check({'AC-1', 'AC-2'}, [str(src_file)], [str(test_file)])
            # Should find SG202 for AC-2 (implemented but not tested)
            sg202_findings = [f for f in findings if f['rule'] == 'SG202']
            self.assertGreater(len(sg202_findings), 0)

    # covers: AC-3
    def test_check_ac_only_in_test(self) -> None:
        """Test check with AC that only has test marker (no implementation)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    assert True\n")

            findings = check({'AC-1'}, [], [str(test_file)])
            # Should find SG201 (tested but not implemented)
            sg201_findings = [f for f in findings if f['rule'] == 'SG201']
            self.assertGreater(len(sg201_findings), 0)

    # covers: AC-3
    def test_check_marker_on_same_line_as_def(self) -> None:
        """Test check with marker on same line as function definition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("def foo():  # implements: AC-1\n    x = 1\n")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def test_foo():  # covers: AC-1\n    assert True\n")

            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            # Should have no violations
            self.assertEqual(len(findings), 0)

    # covers: AC-3
    def test_check_empty_source_files(self) -> None:
        """Test check with empty source files list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    assert True\n")

            findings = check({'AC-1'}, [], [str(test_file)])
            # Should find SG201 (tested but not implemented)
            self.assertGreater(len(findings), 0)

    # covers: AC-3
    def test_check_empty_test_files(self) -> None:
        """Test check with empty test files list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    x = 1\n")

            findings = check({'AC-1'}, [str(src_file)], [])
            # Should find SG202 (implemented but not tested)
            self.assertGreater(len(findings), 0)


class TestCheckExceptionHandling(unittest.TestCase):
    """Test exception handling in check function."""

    # covers: AC-3
    def test_check_with_unreadable_source_file(self) -> None:
        """Test check handles unreadable source files gracefully."""
        findings = check({'AC-1'}, ["/nonexistent/path.py"], [])
        # Exception caught; the only finding is that AC-1 has no markers.
        self.assertEqual([f['rule'] for f in findings], ['SG206'])

    # covers: AC-3
    def test_check_with_unreadable_test_file(self) -> None:
        """Test check handles unreadable test files gracefully."""
        findings = check({'AC-1'}, [], ["/nonexistent/path.py"])
        # Exception caught; the only finding is that AC-1 has no markers.
        self.assertEqual([f['rule'] for f in findings], ['SG206'])


class TestScanMarkersExceptionHandling(unittest.TestCase):
    """Test exception handling in scan_markers."""

    # covers: AC-3
    def test_scan_markers_with_unreadable_src_dir(self) -> None:
        """Test scan_markers handles unreadable source directory."""
        markers = scan_markers(["/nonexistent/src"], [])
        self.assertEqual(len(markers), 0)

    # covers: AC-3
    def test_scan_markers_with_unreadable_test_dir(self) -> None:
        """Test scan_markers handles unreadable test directory."""
        markers = scan_markers([], ["/nonexistent/test"])
        self.assertEqual(len(markers), 0)

    # covers: AC-3
    def test_scan_markers_exception_in_src(self) -> None:
        """Test scan_markers with exception during source file reading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file that will cause unicode decode error
            src_file = Path(tmpdir) / "src.py"
            src_file.write_bytes(b'\x80\x81\x82')

            markers = scan_markers([tmpdir], [])
            # Should handle the exception and return empty markers
            self.assertEqual(len(markers), 0)

    # covers: AC-3
    def test_scan_markers_exception_in_test(self) -> None:
        """Test scan_markers with exception during test file reading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file that will cause unicode decode error
            test_file = Path(tmpdir) / "test.py"
            test_file.write_bytes(b'\x80\x81\x82')

            markers = scan_markers([], [tmpdir])
            # Should handle the exception and return empty markers
            self.assertEqual(len(markers), 0)


class TestCheckMultipleMarkers(unittest.TestCase):
    """Test check function with multiple markers in same AC."""

    # covers: AC-3
    def test_check_multiple_implementations_same_ac(self) -> None:
        """Test check with multiple implementations of same AC."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("""# implements: AC-1
def foo():
    x = 1

# implements: AC-1
def bar():
    y = 2
""")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_ac1():\n    assert True\n")

            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            # Should have no violations
            self.assertEqual(len(findings), 0)

    # covers: AC-3
    def test_check_multiple_tests_same_ac(self) -> None:
        """Test check with multiple tests covering same AC."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    x = 1\n")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("""# covers: AC-1
def test_ac1_case1():
    assert True

# covers: AC-1
def test_ac1_case2():
    assert True
""")

            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            # Should have no violations
            self.assertEqual(len(findings), 0)

    # covers: AC-3
    def test_check_covers_marker_in_source(self) -> None:
        """Test check ignores covers marker when scanning source files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            # A 'covers' marker in source should be ignored during src scan
            src_file.write_text("# covers: AC-1\ndef foo():\n    x = 1\n")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# covers: AC-1\ndef test_foo():\n    assert True\n")

            # foo() not marked with 'implements', test marked with 'covers'
            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            # Should find SG201 (tested but not implemented)
            sg201_findings = [f for f in findings if f['rule'] == 'SG201']
            self.assertGreater(len(sg201_findings), 0)

    # covers: AC-3
    def test_check_implements_marker_in_test(self) -> None:
        """Test check ignores implements marker when scanning test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            src_file.write_text("# implements: AC-1\ndef foo():\n    x = 1\n")

            test_file = Path(tmpdir) / "test.py"
            # An 'implements' marker in test should be ignored during test scan
            test_file.write_text("# implements: AC-1\ndef test_foo():\n    assert True\n")

            # test_foo() not marked with 'covers', foo() marked with 'implements'
            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            # Should find SG202 (implemented but not tested)
            sg202_findings = [f for f in findings if f['rule'] == 'SG202']
            self.assertGreater(len(sg202_findings), 0)

    # covers: AC-3
    def test_check_invalid_marker_format(self) -> None:
        """Test check with invalid marker comment that returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "src.py"
            # Invalid marker that won't parse
            src_file.write_text("# not a marker\ndef foo():\n    x = 1\n")

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# also not a marker\ndef test_foo():\n    assert True\n")

            findings = check({'AC-1'}, [str(src_file)], [str(test_file)])
            # A non-marker comment is not a marker: AC-1 is simply unmarked.
            self.assertEqual([f['rule'] for f in findings], ['SG206'])
