#!/usr/bin/env python3
"""
Generate tool-specific persona exports from neutral source files.

Usage:
    python export.py            # regenerate personas/export/
    python export.py --check    # check for drift, exit 1 if out of sync
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter (simple key: value parsing, no external deps)."""
    if not content.startswith("---"):
        raise ValueError("File must start with ---")

    # Find the closing ---
    lines = content.split("\n")
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise ValueError("No closing --- found")

    frontmatter_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1:]).strip()

    # Parse frontmatter (key: value, key: [list], or key: multiline list)
    fm = {}
    i = 0
    while i < len(frontmatter_lines):
        line = frontmatter_lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Check if this line has a key
        if not line.startswith(" ") and ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()

            # Handle list values [a, b, c] on same line
            if val.startswith("[") and val.endswith("]"):
                items = val[1:-1].split(",")
                val = [item.strip() for item in items]
            # Handle multiline YAML lists (next lines start with -)
            elif val == "" and i + 1 < len(frontmatter_lines) and frontmatter_lines[i + 1].strip().startswith("-"):
                items = []
                j = i + 1
                while j < len(frontmatter_lines) and frontmatter_lines[j].strip().startswith("-"):
                    item = frontmatter_lines[j].strip()[1:].strip()
                    # Remove quotes if present
                    if item.startswith('"') and item.endswith('"'):
                        item = item[1:-1]
                    items.append(item)
                    j += 1
                val = items
                i = j - 1  # Skip the list items we just processed

            fm[key] = val

        i += 1

    return fm, body


def load_personas(personas_dir: str) -> List[Dict[str, Any]]:
    """Load all persona files from the personas directory."""
    personas = []
    personas_path = Path(personas_dir)

    for persona_file in sorted(personas_path.glob("*.persona.md")):
        with open(persona_file, "r") as f:
            content = f.read()

        fm, body = parse_frontmatter(content)
        fm["body"] = body
        fm["source_file"] = persona_file.name
        personas.append(fm)

    return personas


def generate_claude_agent(persona: Dict[str, Any]) -> str:
    """Generate Claude Code subagent markdown."""
    fm = persona
    body = fm.get("body", "")

    # Extract first sentence (identity sentence) from the body
    # For simplicity, use the first non-empty line after headings
    lines = body.split("\n")
    identity_sentence = ""
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            identity_sentence = stripped
            break

    capabilities_section = ""
    output_rule_section = ""
    rules_section = ""

    # Extract sections from body
    current_section = None
    section_content = []

    for line in lines:
        if line.startswith("## Voice"):
            current_section = "voice"
        elif line.startswith("## Operating procedure"):
            current_section = "operating"
        elif line.startswith("## Example prompts"):
            current_section = "examples"
        elif line.startswith("## Failure modes"):
            current_section = "failures"
        elif line.startswith("##"):
            current_section = None
        elif current_section == "voice":
            section_content.append(line)
        elif current_section == "operating":
            section_content.append(line)

    voice_text = "\n".join(section_content[:10]).strip() if section_content else ""

    # Capabilities: extract from Operating procedure section
    capabilities_section = "- Answer questions about this persona's domain\n- Evaluate work against this persona's criteria\n- Provide feedback on specification or implementation"

    # Output Rule
    output_rule_section = f"Respond as {fm.get('name', '')}: maintain the voice and approach described in your identity."

    # Rules: derived from the persona definition
    rules_section = "- Always cite specific evidence when making claims\n- Distinguish between opinion and fact\n- Ask clarifying questions before proceeding if requirements are unclear"

    frontmatter = f"""---
name: {fm.get('name', '')}
description: {fm.get('one_liner', '')}
model: sonnet
---

{identity_sentence}

## Capabilities

{capabilities_section}

## Output Rule

{output_rule_section}

## Rules

{rules_section}"""

    return frontmatter.strip()


def generate_claude_skill(persona: Dict[str, Any]) -> str:
    """Generate Claude Code skill markdown."""
    fm = persona

    # Skill ID to use in the when-to-invoke bullet
    skill_id = fm.get("id", "")

    frontmatter = f"""---
name: {fm.get('name', '')}
description: {fm.get('one_liner', '')}
---

## Purpose

{fm.get('name', '')} specializes in {fm.get('one_liner', '').lower()}

## When to Invoke

- User types `/{skill_id}`
- Work needs {fm.get('one_liner', '').lower()}
- You need feedback on: {', '.join(fm.get('asks_for', [])[:2])}

## Process

1. Understand the context and what's being evaluated
2. Apply the persona's specific methodology
3. Provide structured, actionable feedback
4. Explain the reasoning behind recommendations

## Output Format

A structured assessment addressing the persona's key dimensions with specific, actionable findings."""

    return frontmatter.strip()


def generate_human_card(persona: Dict[str, Any]) -> str:
    """Generate human-readable one-pager card."""
    fm = persona

    asks_for = fm.get("asks_for", [])
    refuses = fm.get("refuses", [])
    produces = fm.get("produces", "")

    asks_str = "\n".join(f"  - {item}" for item in asks_for) if isinstance(asks_for, list) else f"  - {asks_for}"
    refuses_str = "\n".join(f"  - {item}" for item in refuses) if isinstance(refuses, list) else f"  - {refuses}"

    body_sections = fm.get("body", "").split("##")

    role_content = ""
    voice_content = ""
    procedure_content = ""
    examples_content = ""
    failures_content = ""

    for section in body_sections:
        if section.strip().startswith("Role"):
            role_content = section.split("\n", 1)[1].strip() if "\n" in section else ""
        elif section.strip().startswith("Voice"):
            voice_content = section.split("\n", 1)[1].strip() if "\n" in section else ""
        elif section.strip().startswith("Operating procedure"):
            procedure_content = section.split("\n", 1)[1].strip() if "\n" in section else ""
        elif section.strip().startswith("Example prompts"):
            examples_content = section.split("\n", 1)[1].strip() if "\n" in section else ""

    card = f"""# {fm.get('name', '')}

**{fm.get('one_liner', '')}**

**Family**: {fm.get('family', '')}

## Asks For

{asks_str}

## Refuses

{refuses_str}

## Produces

{produces}

## Role

{role_content}

## Voice

{voice_content}

## When to Invoke

{fm.get('invoke_when', '')}

## Operating Procedure

{procedure_content[:200]}...

## Examples

{examples_content[:200]}...

---

*This is a tool-neutral persona. Generated from `{fm.get('source_file', '')}`. Do not edit this file directly.*"""

    return card.strip()


def generate_json(personas: List[Dict[str, Any]]) -> str:
    """Generate portable JSON with all personas."""
    output = []

    for persona in personas:
        entry = {
            "id": persona.get("id", ""),
            "name": persona.get("name", ""),
            "family": persona.get("family", ""),
            "one_liner": persona.get("one_liner", ""),
            "invoke_when": persona.get("invoke_when", ""),
            "asks_for": persona.get("asks_for", []) if isinstance(persona.get("asks_for", []), list) else [persona.get("asks_for", "")],
            "refuses": persona.get("refuses", []) if isinstance(persona.get("refuses", []), list) else [persona.get("refuses", "")],
            "produces": persona.get("produces", ""),
            "source_file": persona.get("source_file", ""),
        }
        output.append(entry)

    return json.dumps(output, indent=2)


def write_exports(personas: List[Dict[str, Any]], export_dir: str) -> None:
    """Write all exports to the export directory."""
    export_path = Path(export_dir)
    export_path.mkdir(exist_ok=True)

    # Create subdirectories
    (export_path / "claude-agents").mkdir(exist_ok=True)
    (export_path / "claude-skills").mkdir(exist_ok=True)
    (export_path / "cards").mkdir(exist_ok=True)

    for persona in personas:
        persona_id = persona.get("id", "")

        # Claude agents
        agent_content = generate_claude_agent(persona)
        agent_file = export_path / "claude-agents" / f"{persona_id}.md"
        header = f"<!-- GENERATED from personas/{persona.get('source_file', '')}. DO NOT EDIT MANUALLY. -->\n\n"
        with open(agent_file, "w") as f:
            f.write(header + agent_content)

        # Claude skills
        skill_content = generate_claude_skill(persona)
        skill_dir = export_path / "claude-skills" / persona_id
        skill_dir.mkdir(exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        with open(skill_file, "w") as f:
            f.write(header + skill_content)

        # Human cards
        card_content = generate_human_card(persona)
        card_file = export_path / "cards" / f"{persona_id}.md"
        with open(card_file, "w") as f:
            f.write(header + card_content)

    # JSON export
    json_content = generate_json(personas)
    json_file = export_path / "personas.json"
    with open(json_file, "w") as f:
        f.write(json_content)


def check_exports(personas: List[Dict[str, Any]], personas_dir: str) -> bool:
    """Check if exports are up to date by generating in a temp dir and comparing."""
    # Generate in temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        write_exports(personas, tmpdir)

        # Compare with actual export directory
        export_dir = Path(personas_dir) / "export"

        if not export_dir.exists():
            print("ERROR: export directory does not exist. Run 'python export.py' to generate exports.")
            return False

        # Check each file
        tmpdir_path = Path(tmpdir)
        for item in tmpdir_path.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(tmpdir_path)
                actual_file = export_dir / rel_path

                if not actual_file.exists():
                    print(f"ERROR: Missing file: export/{rel_path}")
                    return False

                with open(item, "r") as f:
                    tmp_content = f.read()
                with open(actual_file, "r") as f:
                    actual_content = f.read()

                if tmp_content != actual_content:
                    print(f"ERROR: File out of sync: export/{rel_path}")
                    return False

        print("OK: All exports are up to date.")
        return True


def main():
    script_dir = Path(__file__).parent
    personas_dir = str(script_dir)
    export_dir = str(script_dir / "export")

    # Load personas
    personas = load_personas(personas_dir)

    if not personas:
        print("ERROR: No persona files found in", personas_dir)
        sys.exit(1)

    print(f"Loaded {len(personas)} personas")

    # Check mode
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        success = check_exports(personas, personas_dir)
        sys.exit(0 if success else 1)

    # Generate mode
    write_exports(personas, export_dir)
    print(f"Generated exports in {export_dir}/")
    print(f"  - {len(personas)} claude-agents/*.md")
    print(f"  - {len(personas)} claude-skills/*/SKILL.md")
    print(f"  - {len(personas)} cards/*.md")
    print(f"  - personas.json")
    print("\nDone. Run 'python export.py --check' to verify.")


if __name__ == "__main__":
    main()
