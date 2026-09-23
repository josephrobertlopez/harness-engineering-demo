"""Filesystem, hashing and serialization helpers.

Everything here is deliberately boring. Two rules the rest of the package
relies on:

* Text is read and written as UTF-8 with LF endings, always. This repo runs on
  Windows, and a stray CRLF silently changes a content hash and pollutes every
  unified diff.
* Writes are atomic. A crash must leave either the old file or the new one,
  never a half-written one, because ``.trace.json`` existing is what the resume
  logic treats as "this rollout finished".
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def read_text_lf(path: Path) -> str:
    """Read UTF-8 text, normalizing CRLF and lone CR to LF."""
    raw = path.read_bytes().decode("utf-8")
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def atomic_write_text(path: Path, text: str) -> None:
    """Write UTF-8/LF text atomically within the destination directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.replace("\r\n", "\n").encode("utf-8")
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        _replace_with_retry(Path(tmp), path)
    except BaseException:
        _quiet_unlink(Path(tmp))
        raise


#: Windows fails `os.replace` with "Access is denied" when anything holds a
#: handle on the destination -- an antivirus scanner or the search indexer
#: opening a file we just wrote is enough. The window is milliseconds, it is
#: not deterministic, and it surfaces as a test that fails on one machine and
#: never on another. Retrying is the standard remedy; the alternative is
#: telling people to disable their antivirus.
_REPLACE_ATTEMPTS = 8
_REPLACE_BACKOFF = 0.02


def _replace_with_retry(src: Path, dst: Path) -> None:
    """`os.replace`, tolerant of a transient Windows lock on `dst`.

    Atomicity is unaffected: each attempt is still a single rename, so the
    destination holds either the old file or the new one at every instant.
    """
    last: OSError | None = None
    for attempt in range(_REPLACE_ATTEMPTS):
        try:
            os.replace(src, dst)
            return
        except PermissionError as exc:  # Windows: something holds a handle
            last = exc
            time.sleep(_REPLACE_BACKOFF * (attempt + 1))
    raise OSError(
        f"could not replace {dst} after {_REPLACE_ATTEMPTS} attempts; "
        "something is holding a handle on it"
    ) from last


def append_text(path: Path, text: str) -> None:
    """Append UTF-8/LF text, creating the file if needed.

    Not atomic by design: the evolution log and the skill-impact ledger are
    append-only journals where a torn final line is recoverable but a lost
    history is not.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as fh:
        fh.write(text.replace("\r\n", "\n").encode("utf-8"))
        fh.flush()
        os.fsync(fh.fileno())


def write_json(path: Path, obj: Any) -> None:
    atomic_write_text(path, canonical_json(obj) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(read_text_lf(path))


def canonical_json(obj: Any) -> str:
    """Stable JSON: sorted keys, no incidental whitespace.

    Used for content hashes and backend cache keys. An unsorted dict here is
    the classic source of "the hash changed but nothing did".
    """
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def content_sha(text: str) -> str:
    """Short, stable content address."""
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()


def slugify(text: str) -> str:
    return _SLUG_STRIP.sub("-", text.strip().lower()).strip("-")


def safe_join(root: Path, relative: str) -> Path:
    """Resolve ``relative`` under ``root``, refusing to escape it.

    Guards the wiki against a model emitting ``patterns/../../skills/x/SKILL.md``
    -- which, given enough iterations, one eventually will.
    """
    if not relative or relative.startswith(("/", "\\")):
        raise ValueError(f"path must be relative: {relative!r}")
    if "\x00" in relative:
        raise ValueError("path contains a null byte")
    candidate = (root / relative).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError(f"path escapes {root_resolved}: {relative!r}")
    return candidate


def copy_tree(src: Path, dst: Path) -> None:
    """Replace ``dst`` with a copy of ``src``."""
    rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)


def rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, onexc=_on_rm_error)


def _on_rm_error(func, path, exc):  # pragma: no cover - Windows read-only files
    os.chmod(path, 0o700)
    func(path)


def _quiet_unlink(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass
