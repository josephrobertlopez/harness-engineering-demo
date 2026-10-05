"""L0 layer for PRD schema validation."""

import subprocess
import json
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional, Callable

import yaml
import jsonschema


def parse_prd(path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Parse YAML frontmatter from a PRD file.

    Returns:
        (frontmatter dict, error string) - error is None if successful
    """
    try:
        with open(path, 'r') as f:
            content = f.read()
    except Exception as e:
        return None, f"Could not read file: {e}"

    # Look for YAML frontmatter between --- lines
    if not content.startswith('---'):
        return None, "No frontmatter found"

    lines = content.split('\n')
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].startswith('---'):
            end_idx = i
            break

    if end_idx is None:
        return None, "No closing --- found for frontmatter"

    frontmatter_str = '\n'.join(lines[1:end_idx])

    try:
        frontmatter = yaml.safe_load(frontmatter_str)
        if frontmatter is None:
            return None, "Frontmatter is empty"
        return frontmatter, None
    except yaml.YAMLError as e:
        return None, f"Invalid YAML: {e}"


def check_prd(path: str) -> List[Dict[str, Any]]:
    """
    Check a PRD file against the schema and rules.

    Returns:
        List of findings, each with keys: rule, file, line, message
    """
    findings = []

    # Load schema
    schema_path = Path(__file__).parent.parent.parent / "schema" / "prd.schema.json"
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except Exception as e:
        findings.append({
            'rule': 'SG005',
            'file': path,
            'line': 0,
            'message': f"Could not load schema: {e}"
        })
        return findings

    # Parse frontmatter
    frontmatter, parse_error = parse_prd(path)

    if parse_error:
        findings.append({
            'rule': 'SG005',
            'file': path,
            'line': 0,
            'message': parse_error
        })
        return findings

    # Validate against schema
    try:
        jsonschema.validate(instance=frontmatter, schema=schema)
    except jsonschema.ValidationError as e:
        findings.append({
            'rule': 'SG001',
            'file': path,
            'line': 0,
            'message': f"Schema validation failed: {e.message}"
        })

    # Check for duplicate AC IDs (SG002)
    if frontmatter and 'acs' in frontmatter:
        ac_ids = {}
        for ac in frontmatter.get('acs', []):
            if isinstance(ac, dict) and 'id' in ac:
                ac_id = ac['id']
                if ac_id in ac_ids:
                    findings.append({
                        'rule': 'SG002',
                        'file': path,
                        'line': 0,
                        'message': f"Duplicate AC ID: {ac_id}"
                    })
                else:
                    ac_ids[ac_id] = True

    # Check for missing required fields in ACs (SG003)
    if frontmatter and 'acs' in frontmatter:
        for i, ac in enumerate(frontmatter.get('acs', [])):
            if isinstance(ac, dict):
                # Check for missing given
                if 'given' not in ac or not ac['given']:
                    findings.append({
                        'rule': 'SG003',
                        'file': path,
                        'line': 0,
                        'message': f"AC {i+1} missing 'given' field"
                    })

                # Check for missing when
                if 'when' not in ac or not ac['when']:
                    findings.append({
                        'rule': 'SG003',
                        'file': path,
                        'line': 0,
                        'message': f"AC {i+1} missing 'when' field"
                    })

                # Check for missing then
                if 'then' not in ac or not ac['then']:
                    findings.append({
                        'rule': 'SG003',
                        'file': path,
                        'line': 0,
                        'message': f"AC {i+1} missing 'then' field"
                    })

                # Check for missing or empty tests
                tests = ac.get('tests', [])
                if not tests or (isinstance(tests, list) and len(tests) == 0):
                    findings.append({
                        'rule': 'SG003',
                        'file': path,
                        'line': 0,
                        'message': f"AC {i+1} missing or empty 'tests' field"
                    })

    return findings


def check_openspec(
    change: str,
    cwd: str,
    runner: Optional[Callable] = None
) -> List[Dict[str, Any]]:
    """
    Check a change using openspec validate.

    Args:
        change: Path to the change file
        cwd: Current working directory
        runner: Callable for running commands (default: subprocess.run)

    Returns:
        List of findings with SG004 rule on failure
    """
    if runner is None:
        runner = subprocess.run

    findings = []

    try:
        result = runner(
            ['npx', '-y', '@fission-ai/openspec@1.14.0', 'validate', change, '--strict'],
            cwd=cwd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            findings.append({
                'rule': 'SG004',
                'file': change,
                'line': 0,
                'message': f"openspec validation failed: {result.stderr or result.stdout}"
            })
    except Exception as e:
        findings.append({
            'rule': 'SG004',
            'file': change,
            'line': 0,
            'message': f"Could not run openspec: {e}"
        })

    return findings


def check(
    prd_path: str,
    change: Optional[str] = None,
    cwd: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Run all L0 checks on a PRD.

    Args:
        prd_path: Path to the PRD file
        change: Path to change file (optional, for SG004)
        cwd: Current working directory (optional, for SG004)

    Returns:
        Combined list of findings
    """
    findings = check_prd(prd_path)

    if change and cwd:
        findings.extend(check_openspec(change, cwd))

    return findings
