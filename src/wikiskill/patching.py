"""Validation and application of wiki patch operations.

Pure functions over an in-memory ``{relative_path: text}`` map. Keeping the
disk out of here is what makes the all-or-nothing guarantee cheap: the whole
batch is applied to a dict first, and only a fully successful batch is handed
back to the caller to write.

Why all-or-nothing matters specifically here: **the wiki is never rolled
back.** A partially applied batch is therefore permanent damage, not a
recoverable state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from .types import PatchOp

PATH_RE = re.compile(r"^patterns/[a-z0-9][a-z0-9-]{1,63}\.md$")


class PatchError(Exception):
    """A patch that failed validation, carrying a stable error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class PatchOutcome:
    pages: dict[str, str]
    """The full post-state. Only meaningful when ``ok`` is True."""
    errors: tuple[tuple[PatchOp, str], ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_path(path: str) -> None:
    if not PATH_RE.match(path):
        raise PatchError(
            "E_PATH",
            f"must match patterns/<slug>.md with a lowercase slug, got {path!r}",
        )


def apply_batch(
    pages: Mapping[str, str],
    ops: Iterable[PatchOp],
    *,
    trace_exists: Callable[[str], bool] | None = None,
) -> PatchOutcome:
    """Apply ``ops`` sequentially to a copy of ``pages``.

    Edit *n* sees edit *n-1*'s output, so a batch can create a page and then
    append to it. The first failure aborts the batch and returns the original
    pages untouched.
    """
    working = dict(pages)
    errors: list[tuple[PatchOp, str]] = []

    for op in ops:
        try:
            _apply_one(working, op, trace_exists)
        except PatchError as exc:
            errors.append((op, str(exc)))
            return PatchOutcome(pages=dict(pages), errors=tuple(errors))

    return PatchOutcome(pages=working, errors=())


def _apply_one(
    pages: dict[str, str],
    op: PatchOp,
    trace_exists: Callable[[str], bool] | None,
) -> None:
    validate_path(op.path)

    # Evidence is checked before anything else mutates. The paper requires
    # pattern pages to carry supporting trace references; enforcing it here
    # makes that structural rather than a request the model may ignore.
    if trace_exists is not None:
        for tid in op.evidence_traces:
            if not trace_exists(tid):
                raise PatchError("E_EVIDENCE", f"cited trace does not resolve: {tid}")

    exists = op.path in pages

    if op.op == "create_page":
        if exists:
            raise PatchError("E_PATH_EXISTS", f"page already exists: {op.path}")
        if not op.evidence_traces:
            raise PatchError("E_EVIDENCE", "a new pattern page must cite at least one trace")
        if not op.content.strip():
            raise PatchError("E_EMPTY", "create_page needs content")
        title = (op.title or op.path).strip()
        pages[op.path] = f"# {title}\n\n{op.content.strip()}\n"
        return

    if not exists:
        raise PatchError("E_PATH_MISSING", f"page does not exist: {op.path}")

    current = pages[op.path]

    if op.op == "append":
        if not op.content.strip():
            raise PatchError("E_EMPTY", "append needs content")
        pages[op.path] = current.rstrip("\n") + "\n\n" + op.content.strip() + "\n"
        return

    if op.op in ("replace", "insert_after"):
        if not op.anchor:
            raise PatchError("E_ANCHOR_MISSING", f"{op.op} requires an anchor")
        hits = current.count(op.anchor)
        if hits == 0:
            raise PatchError("E_ANCHOR_MISSING", f"anchor not found in {op.path}")
        if hits > 1:
            # "First occurrence" semantics silently corrupt pages as they grow,
            # which on a never-rolled-back layer is unrecoverable.
            raise PatchError("E_ANCHOR_AMBIGUOUS", f"anchor occurs {hits} times in {op.path}")
        if op.op == "replace":
            pages[op.path] = current.replace(op.anchor, op.content, 1)
        else:
            pages[op.path] = current.replace(op.anchor, op.anchor + "\n" + op.content, 1)
        return

    raise PatchError("E_OP", f"unknown op: {op.op!r}")
