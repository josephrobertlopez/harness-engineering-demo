"""Trace module for generating trace.json with AC implementation and test coverage information."""

import json
from pathlib import Path
from typing import Any

from specgate.l2_trace import scan_markers


def gather_trace_data(
    ac_ids: set[str],
    src_dirs: list[str],
    test_dirs: list[str],
    junit_path: str | None = None,
) -> dict[str, Any]:
    """
    Gather trace data from implementation markers, test coverage, and mutation testing.

    Args:
        ac_ids: Set of known AC IDs
        src_dirs: List of source directories
        test_dirs: List of test directories
        junit_path: Path to junit XML file (optional)

    Returns:
        Trace data dictionary with AC mappings
    """
    trace: dict[str, Any] = {}

    # Scan for markers in source and test files
    markers = scan_markers(src_dirs, test_dirs)

    # Build AC trace
    for ac_id in sorted(ac_ids):
        ac_trace: dict[str, Any] = {"id": ac_id}

        # Implementations
        impl_locs = []
        if ac_id in markers:
            for marker in markers[ac_id]:
                if marker.marker_type == "implements":
                    # Normalize paths to be relative to repo root
                    file_path = str(Path(marker.file))
                    impl_locs.append({
                        "file": file_path,
                        "function": marker.funcname,
                        "line": marker.line,
                    })
        ac_trace["implements"] = impl_locs

        # Test functions that cover the AC
        covers_locs = []
        if ac_id in markers:
            for marker in markers[ac_id]:
                if marker.marker_type == "covers":
                    file_path = str(Path(marker.file))
                    covers_locs.append({
                        "file": file_path,
                        "function": marker.funcname,
                        "line": marker.line,
                    })
        ac_trace["covers"] = covers_locs

        # JUnit status (from L3)
        ac_trace["junit"] = None

        # Coverage data (from L4)
        ac_trace["coverage"] = {
            "lines_covered": 0,
            "lines_total": 0,
        }

        # Mutation data (from L5)
        ac_trace["mutations"] = {
            "killed": 0,
            "total": 0,
        }

        trace[ac_id] = ac_trace

    return trace


def write_trace_json(trace_data: dict[str, Any], output_path: str) -> None:
    """
    Write trace data to JSON file with sorted keys and no timestamps.

    Args:
        trace_data: Trace data dictionary
        output_path: Path to output JSON file
    """
    with open(output_path, 'w') as f:
        json.dump(
            trace_data,
            f,
            sort_keys=True,
            indent=2,
        )
        # Add newline at end
        f.write('\n')


def generate_trace(
    ac_ids: set[str],
    src_dirs: list[str],
    test_dirs: list[str],
    output_path: str = "trace.json",
    junit_path: str | None = None,
) -> None:
    """
    Generate and write trace.json file.

    Args:
        ac_ids: Set of known AC IDs
        src_dirs: List of source directories
        test_dirs: List of test directories
        output_path: Path to write trace.json
        junit_path: Path to junit XML file (optional)
    """
    trace_data = gather_trace_data(
        ac_ids,
        src_dirs,
        test_dirs,
        junit_path=junit_path,
    )
    write_trace_json(trace_data, output_path)
