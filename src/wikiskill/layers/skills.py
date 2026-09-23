"""The Skills layer: content-addressed snapshots behind one atomic pointer.

Nothing is ever edited in place.

    .state/skillsets/<sha>/<name>/{SKILL.md,PURPOSE.md}   immutable snapshots
    .state/HEAD.json                                      {"sha", "iter", "r_best"}
    skills/                                               mirror of HEAD, for humans

Accepting a proposal moves HEAD. Rejecting one does nothing at all -- the
candidate snapshot is simply never pointed at. There is no undo path to get
wrong, which is the entire reason for the indirection.

Why a pointer *file* rather than swapping a directory: ``os.replace`` onto an
existing non-empty directory fails on Windows, so a directory swap would need
a delete-then-rename window that is not crash-safe. Replacing a small JSON
file has no such window.
"""

from __future__ import annotations

import difflib
from pathlib import Path

from ..types import Skill, SkillSet
from ..util import atomic_write_text, copy_tree, read_json, read_text_lf, rmtree, write_json


class SkillSetStore:
    def __init__(self, snapshots: Path, head_path: Path, mirror: Path) -> None:
        self.snapshots = snapshots
        self.head_path = head_path
        self.mirror = mirror

    # -- snapshots --------------------------------------------------------

    def materialize(self, skillset: SkillSet) -> str:
        """Write ``skillset`` to its content-addressed snapshot; return the sha.

        Idempotent: identical content hashes to the same sha, so re-running
        this phase after a crash rewrites the same bytes rather than forking a
        new lineage.
        """
        sha = skillset.sha
        dest = self.snapshots / sha
        if dest.exists():
            return sha
        staging = self.snapshots / f".tmp-{sha}"
        rmtree(staging)
        for skill in skillset.sorted():
            d = staging / skill.name
            d.mkdir(parents=True, exist_ok=True)
            atomic_write_text(d / "SKILL.md", skill.skill_md())
            atomic_write_text(d / "PURPOSE.md", skill.purpose_md())
        staging.mkdir(parents=True, exist_ok=True)
        # `os.replace` maps to MoveFileEx(MOVEFILE_REPLACE_EXISTING), which
        # refuses directories on Windows -- it fails with "Access is denied"
        # even when the destination does not exist. A plain rename onto a
        # non-existent path is the portable form.
        try:
            staging.rename(dest)
        except OSError:
            # Lost a race, or a scanner has a handle on the staging dir.
            # The snapshot is content-addressed, so if the destination now
            # exists it holds exactly these bytes and copying is unnecessary.
            if not dest.exists():
                copy_tree(staging, dest)
            rmtree(staging)
        return sha

    def load(self, sha: str) -> SkillSet:
        root = self.snapshots / sha
        if not root.exists():
            raise FileNotFoundError(f"no skill snapshot {sha}")
        skills = []
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            skills.append(_read_skill(d))
        return SkillSet(skills=tuple(skills))

    def snapshot_dir(self, sha: str) -> Path:
        return self.snapshots / sha

    # -- HEAD -------------------------------------------------------------

    def head(self) -> dict:
        if not self.head_path.exists():
            empty = SkillSet()
            sha = self.materialize(empty)
            state = {"sha": sha, "iter": 0, "r_best": 0.0}
            write_json(self.head_path, state)
            self.rebuild_mirror(sha)
            return state
        return read_json(self.head_path)

    def set_head(self, sha: str, iteration: int, r_best: float) -> None:
        write_json(self.head_path, {"sha": sha, "iter": iteration, "r_best": r_best})
        self.rebuild_mirror(sha)

    def head_skillset(self) -> SkillSet:
        return self.load(self.head()["sha"])

    # -- mirror -----------------------------------------------------------

    def rebuild_mirror(self, sha: str) -> None:
        """Refresh the human-readable ``skills/`` copy of HEAD.

        Idempotent, so a crash between the HEAD move and this call is repaired
        by simply calling it again on the next startup.
        """
        copy_tree(self.snapshots / sha, self.mirror)

    def mirror_is_stale(self) -> bool:
        try:
            current = self.head()["sha"]
        except (FileNotFoundError, KeyError):
            return True
        if not self.mirror.exists():
            return True
        skills = [_read_skill(d) for d in sorted(p for p in self.mirror.iterdir() if p.is_dir())]
        return SkillSet(skills=tuple(skills)).sha != current

    # -- diffing ----------------------------------------------------------

    def unified_diff(self, before: SkillSet, after: SkillSet) -> str:
        """Tree-level unified diff, from ``difflib``.

        Deliberately not ``git diff``: the workspace already lives inside the
        user's repository, so a nested git repo would be a second VCS managing
        a directory that is already versioned. ``difflib`` output is also a
        pure function of two strings, where ``git diff`` varies with
        ``core.autocrlf`` and ``diff.algorithm`` -- which matters on Windows.
        """
        a = _tree(before)
        b = _tree(after)
        out: list[str] = []
        for rel in sorted(set(a) | set(b)):
            left = a.get(rel, "").splitlines(keepends=True)
            right = b.get(rel, "").splitlines(keepends=True)
            if left == right:
                continue
            out.extend(
                difflib.unified_diff(
                    left,
                    right,
                    fromfile=f"a/skills/{rel}" if rel in a else "/dev/null",
                    tofile=f"b/skills/{rel}" if rel in b else "/dev/null",
                    n=3,
                )
            )
        return "".join(out)


def _tree(skillset: SkillSet) -> dict[str, str]:
    tree: dict[str, str] = {}
    for s in skillset.sorted():
        tree[f"{s.name}/SKILL.md"] = s.skill_md()
        tree[f"{s.name}/PURPOSE.md"] = s.purpose_md()
    return tree


def _read_skill(d: Path) -> Skill:
    skill_md = read_text_lf(d / "SKILL.md")
    purpose_md = read_text_lf(d / "PURPOSE.md") if (d / "PURPOSE.md").exists() else ""
    description, body = _split_frontmatter(skill_md)
    purpose, patterns = _split_purpose(purpose_md)
    return Skill(
        name=d.name,
        description=description,
        body=body,
        purpose=purpose,
        source_patterns=patterns,
    )


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text.strip()
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text.strip()
    head = text[4:end]
    body = text[end + 5 :]
    description = ""
    for line in head.splitlines():
        if line.startswith("description:"):
            description = line.split(":", 1)[1].strip()
    return description, body.strip()


def _split_purpose(text: str) -> tuple[str, tuple[str, ...]]:
    marker = "## Motivating wiki patterns"
    if marker not in text:
        return text.strip(), ()
    head, tail = text.split(marker, 1)
    head = head.split("\n", 1)[-1] if head.startswith("# ") else head
    patterns = tuple(
        ln.lstrip("- ").strip()
        for ln in tail.splitlines()
        if ln.strip().startswith("- ") and "(none recorded)" not in ln
    )
    return head.strip(), patterns
