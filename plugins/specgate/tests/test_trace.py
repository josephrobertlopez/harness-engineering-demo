"""Tests for trace module."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from specgate.trace import (
    gather_trace_data,
    generate_trace,
    write_trace_json,
)


class TestGatherTraceData(unittest.TestCase):
    """Test trace data gathering."""

    def test_gather_trace_empty_ac_ids(self):
        """Test gathering trace with no AC IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = gather_trace_data(set(), [tmpdir], [tmpdir])
            self.assertEqual(trace, {})

    def test_gather_trace_single_ac(self):
        """Test gathering trace with single AC."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "impl.py"
            src_file.write_text("""
# implements: AC-1
def feature():
    return True
""")
            test_file = Path(tmpdir) / "test_impl.py"
            test_file.write_text("""
# covers: AC-1
def test_feature():
    from impl import feature
    assert feature() is True
""")

            trace = gather_trace_data(
                {"AC-1"},
                [str(Path(tmpdir))],
                [str(Path(tmpdir))],
            )

            self.assertIn("AC-1", trace)
            ac_trace = trace["AC-1"]
            self.assertEqual(ac_trace["id"], "AC-1")
            self.assertGreater(len(ac_trace["implements"]), 0)
            self.assertGreater(len(ac_trace["covers"]), 0)

    def test_gather_trace_multiple_acs(self):
        """Test gathering trace with multiple ACs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "impl.py"
            src_file.write_text("""
# implements: AC-1
def feature1():
    return True

# implements: AC-2
def feature2():
    return False
""")

            trace = gather_trace_data(
                {"AC-1", "AC-2"},
                [str(Path(tmpdir))],
                [],
            )

            self.assertIn("AC-1", trace)
            self.assertIn("AC-2", trace)


class TestWriteTraceJSON(unittest.TestCase):
    """Test trace JSON writing."""

    def test_write_trace_json_sorted_keys(self):
        """Test that trace JSON is written with sorted keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "trace.json")
            trace_data = {
                "AC-2": {"id": "AC-2", "implements": []},
                "AC-1": {"id": "AC-1", "implements": []},
            }

            write_trace_json(trace_data, output_file)

            # Read and verify
            with open(output_file, 'r') as f:
                content = f.read()
                # Check that JSON is valid
                parsed = json.loads(content)
                self.assertEqual(list(parsed.keys()), ["AC-1", "AC-2"])

    def test_write_trace_json_newline(self):
        """Test that trace JSON ends with newline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "trace.json")
            trace_data = {"AC-1": {"id": "AC-1"}}

            write_trace_json(trace_data, output_file)

            with open(output_file, 'rb') as f:
                content = f.read()
                self.assertTrue(content.endswith(b'\n'))

    def test_write_trace_json_no_timestamps(self):
        """Test that trace JSON contains no timestamps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "trace.json")
            trace_data = {"AC-1": {"id": "AC-1"}}

            write_trace_json(trace_data, output_file)

            with open(output_file, 'r') as f:
                content = f.read()
                # Check for common timestamp patterns
                self.assertNotIn("timestamp", content.lower())
                self.assertNotIn("date", content.lower())
                self.assertNotIn("2024", content)
                self.assertNotIn("2025", content)
                self.assertNotIn("2026", content)

    def test_write_trace_json_indent(self):
        """Test that trace JSON is properly indented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "trace.json")
            trace_data = {
                "AC-1": {
                    "id": "AC-1",
                    "implements": [{"file": "test.py", "line": 1}],
                }
            }

            write_trace_json(trace_data, output_file)

            with open(output_file, 'r') as f:
                content = f.read()
                # Check for indentation (should have leading spaces)
                lines = content.split('\n')
                self.assertTrue(any(line.startswith('  ') for line in lines))

    def test_write_trace_json_byte_identical(self):
        """Test that writing same data produces byte-identical output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file1 = os.path.join(tmpdir, "trace1.json")
            output_file2 = os.path.join(tmpdir, "trace2.json")
            trace_data = {"AC-1": {"id": "AC-1"}}

            write_trace_json(trace_data, output_file1)
            write_trace_json(trace_data, output_file2)

            with open(output_file1, 'rb') as f1:
                content1 = f1.read()
            with open(output_file2, 'rb') as f2:
                content2 = f2.read()

            self.assertEqual(content1, content2)


class TestGenerateTrace(unittest.TestCase):
    """Test trace generation."""

    def test_generate_trace_creates_file(self):
        """Test that generate_trace creates output file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "trace.json")

            generate_trace(
                {"AC-1"},
                [tmpdir],
                [tmpdir],
                output_path=output_file,
            )

            self.assertTrue(os.path.exists(output_file))
            with open(output_file, 'r') as f:
                data = json.load(f)
                self.assertIn("AC-1", data)

    def test_generate_trace_default_output(self):
        """Test generate_trace with default output path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory to ensure file is created there
            cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                generate_trace(
                    {"AC-1"},
                    [tmpdir],
                    [tmpdir],
                )
                self.assertTrue(os.path.exists("trace.json"))
            finally:
                os.chdir(cwd)


class TestTraceStructure(unittest.TestCase):
    """Test trace JSON structure."""

    def test_trace_structure_ac_mapping(self):
        """Test that trace correctly maps ACs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "trace.json")

            generate_trace(
                {"AC-1", "AC-2"},
                [tmpdir],
                [tmpdir],
                output_path=output_file,
            )

            with open(output_file, 'r') as f:
                data = json.load(f)

            # Each AC should have required fields
            for ac_id in ["AC-1", "AC-2"]:
                self.assertIn(ac_id, data)
                ac = data[ac_id]
                self.assertIn("id", ac)
                self.assertIn("implements", ac)
                self.assertIn("covers", ac)
                self.assertEqual(set(ac), {"id", "implements", "covers"})

    def test_trace_implements_field(self):
        """Test trace implements field structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "impl.py"
            src_file.write_text("""
# implements: AC-1
def feature():
    pass
""")
            output_file = os.path.join(tmpdir, "trace.json")

            generate_trace(
                {"AC-1"},
                [tmpdir],
                [tmpdir],
                output_path=output_file,
            )

            with open(output_file, 'r') as f:
                data = json.load(f)

            ac = data["AC-1"]
            self.assertIsInstance(ac["implements"], list)
            if ac["implements"]:
                impl = ac["implements"][0]
                self.assertIn("file", impl)
                self.assertIn("function", impl)
                self.assertIn("line", impl)

    def test_trace_covers_field(self):
        """Test trace covers field structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("""
# covers: AC-1
def test_feature():
    assert True
""")
            output_file = os.path.join(tmpdir, "trace.json")

            generate_trace(
                {"AC-1"},
                [tmpdir],
                [tmpdir],
                output_path=output_file,
            )

            with open(output_file, 'r') as f:
                data = json.load(f)

            ac = data["AC-1"]
            self.assertIsInstance(ac["covers"], list)
            if ac["covers"]:
                cover = ac["covers"][0]
                self.assertIn("file", cover)
                self.assertIn("function", cover)
                self.assertIn("line", cover)


if __name__ == '__main__':
    unittest.main()
