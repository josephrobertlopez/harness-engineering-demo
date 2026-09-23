"""A small records-service benchmark, built to make skill evolution visible.

Twenty tasks across five *quirk families*. Every family hides one rule that a
competent agent cannot infer from the task prompt alone -- it has to discover
the rule by failing, which is exactly the signal the Wiki Maintainer is
supposed to compile and the Skill Proposer is supposed to encode.

    iso_z        timestamps must be emitted as ISO-8601 with a trailing Z
    rec_prefix   fetch only accepts the canonical uppercase REC- form
    page_two     search paginates at three hits; the answer is often on page 2
    round_even   money rounds half-to-even at 2dp, not half-up
    idem_key     write payloads must carry idempotency_key = "<record>:<op>"

Four instances per family: two train, one val, one test. The splits are
disjoint by construction, so a skill that memorises a train answer scores
nothing on val.
"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from ..types import Task, Trace

FAMILIES = ("iso_z", "rec_prefix", "page_two", "round_even", "idem_key")

#: Marker the mock backend looks for in a skill body to decide whether the
#: agent "knows" a family's rule. Real models read the prose, not the marker;
#: this exists so the offline end-to-end test can assert genuine improvement
#: instead of merely asserting that nothing threw.
QUIRK_TOKEN = "[[QUIRK:{family}]]"

_SPLIT_BY_INSTANCE = {0: "train", 1: "train", 2: "val", 3: "test"}

_TIMESTAMPS = ["2026-03-04 11:02:33", "2026-03-05 09:14:00", "2026-03-06 23:47:51", "2026-03-07 06:30:12"]
_OWNERS = ["nordvik", "achebe", "ramaswamy", "okonkwo"]
# Every value must round differently under half-even and half-up, or the
# task would pass without the skill and the split would carry no signal.
_AMOUNTS = ["2.345", "18.125", "7.665", "40.485"]
_STATUSES = ["settled", "pending", "settled", "reversed"]


def _rid(family: str, instance: int) -> str:
    return f"REC-{4800 + FAMILIES.index(family) * 10 + instance}"


def _expected(family: str, instance: int) -> dict[str, Any]:
    rid = _rid(family, instance)
    if family == "iso_z":
        return {"record_id": rid, "timestamp": _TIMESTAMPS[instance].replace(" ", "T") + "Z"}
    if family == "rec_prefix":
        return {"record_id": rid, "status": _STATUSES[instance]}
    if family == "page_two":
        return {"record_id": rid, "owner": _OWNERS[instance]}
    if family == "round_even":
        quantized = Decimal(_AMOUNTS[instance]).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        return {"record_id": rid, "amount": float(quantized)}
    if family == "idem_key":
        return {"record_id": rid, "operation": "reconcile", "idempotency_key": f"{rid}:reconcile"}
    raise ValueError(family)


def _prompt(family: str, instance: int) -> str:
    rid = _rid(family, instance)
    lower = rid.lower()
    if family == "iso_z":
        return (
            f"Look up record {rid} and report its timestamp.\n"
            'Answer with JSON: {"record_id": ..., "timestamp": ...}'
        )
    if family == "rec_prefix":
        return (
            f"Search for the record matching '{lower}' and report its settlement status.\n"
            'Answer with JSON: {"record_id": ..., "status": ...}'
        )
    if family == "page_two":
        return (
            f"Search the ledger for '{_OWNERS[instance]}' and report the owner of record {rid}.\n"
            'Answer with JSON: {"record_id": ..., "owner": ...}'
        )
    if family == "round_even":
        return (
            f"Look up record {rid} and report its amount rounded to 2 decimal places.\n"
            'Answer with JSON: {"record_id": ..., "amount": ...}'
        )
    if family == "idem_key":
        return (
            f"Build the payload that reconciles record {rid}.\n"
            'Answer with JSON: {"record_id": ..., "operation": ..., "idempotency_key": ...}'
        )
    raise ValueError(family)


def tasks() -> list[Task]:
    out: list[Task] = []
    for family in FAMILIES:
        for instance in range(4):
            split = _SPLIT_BY_INSTANCE[instance]
            out.append(
                Task(
                    task_id=f"{family}-{instance}",
                    split=split,  # type: ignore[arg-type]
                    family=family,
                    prompt=_prompt(family, instance),
                    env_spec={"family": family, "instance": instance},
                    expected=_expected(family, instance),
                )
            )
    return out


TOOL_SPEC = """\
search  {"query": "<text>", "page": <int, default 1>}
        Returns up to 3 record ids per page, plus whether more pages exist.
fetch   {"record_id": "<id>"}
        Returns the raw stored record as JSON.
"""


class StarterEnv:
    """Deterministic simulated records service. No network, no clock."""

    def __init__(self, task: Task) -> None:
        self.family: str = task.env_spec["family"]
        self.instance: int = task.env_spec["instance"]
        self.record_id = _rid(self.family, self.instance)

    def tool_spec(self) -> str:
        return TOOL_SPEC

    def call(self, name: str, args: dict[str, Any]) -> str:
        if name == "search":
            return self._search(str(args.get("query", "")), int(args.get("page", 1) or 1))
        if name == "fetch":
            return self._fetch(str(args.get("record_id", "")))
        return f'ERROR: unknown tool {name!r}. Available: search, fetch.'

    # -- tools ------------------------------------------------------------

    def _search(self, query: str, page: int) -> str:
        hits = [f"decoy-{self.instance}{i}" for i in range(3)]
        target = self.record_id.lower()
        if self.family == "page_two":
            # The answer sits on page 2. An agent that never paginates will
            # confidently report a decoy.
            if page <= 1:
                return json.dumps({"page": 1, "results": hits, "more_pages": True})
            return json.dumps({"page": 2, "results": [target], "more_pages": False})
        if page > 1:
            return json.dumps({"page": page, "results": [], "more_pages": False})
        return json.dumps({"page": 1, "results": [target] + hits[:2], "more_pages": False})

    def _fetch(self, record_id: str) -> str:
        if self.family == "rec_prefix":
            # Case- and prefix-sensitive on purpose. Search hands back the
            # lowercase form, so the obvious copy-paste fails.
            if record_id != self.record_id:
                return (
                    f'ERROR: no record {record_id!r}. '
                    "Ids are canonical uppercase with a REC- prefix."
                )
        elif record_id.upper().removeprefix("REC-") != self.record_id.removeprefix("REC-"):
            return f'ERROR: no record {record_id!r}.'
        return json.dumps(self._record())

    def _record(self) -> dict[str, Any]:
        base: dict[str, Any] = {"record_id": self.record_id, "ledger": "primary"}
        if self.family == "iso_z":
            base["timestamp"] = _TIMESTAMPS[self.instance]
            base["timezone"] = "UTC"
        elif self.family == "rec_prefix":
            base["status"] = _STATUSES[self.instance]
        elif self.family == "page_two":
            base["owner"] = _OWNERS[self.instance]
        elif self.family == "round_even":
            base["amount_raw"] = _AMOUNTS[self.instance]
            base["currency"] = "USD"
        elif self.family == "idem_key":
            base["operation"] = "reconcile"
        return base


def score(task: Task, answer: dict[str, Any] | None) -> tuple[float, str | None]:
    """Per-field partial credit; a task passes only at 1.0.

    Pure and deterministic -- no LLM judge. The gate's comparison is only as
    trustworthy as the scorer underneath it.
    """
    expected = task.expected
    if answer is None:
        return 0.0, "no parseable JSON answer"
    correct = 0
    first_bad: str | None = None
    for key, want in expected.items():
        got = answer.get(key)
        if _equal(got, want):
            correct += 1
        elif first_bad is None:
            first_bad = f"field {key!r}: expected {want!r}, got {got!r}"
    value = correct / len(expected)
    return value, None if value == 1.0 else first_bad


def _equal(got: Any, want: Any) -> bool:
    if isinstance(want, float):
        try:
            return abs(float(got) - want) < 1e-9
        except (TypeError, ValueError):
            return False
    return got == want


def summarize(traces: list[Trace]) -> str:
    """Per-family pass counts, handed to the Wiki Maintainer as an overview."""
    rows: dict[str, list[int]] = {}
    for t in traces:
        bucket = rows.setdefault(t.family, [0, 0])
        bucket[1] += 1
        if t.passed:
            bucket[0] += 1
    return "\n".join(
        f"- {family}: {passed}/{total} passed" for family, (passed, total) in sorted(rows.items())
    )
