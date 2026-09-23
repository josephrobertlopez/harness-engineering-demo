"""Deterministic offline backend, and the load-bearing test fixture.

A mock that returns canned text proves only that the pipeline does not throw.
This one is **skill-sensitive**: the simulated inference agent answers a task
correctly if and only if the skill set injected into its prompt actually
covers that task's quirk family. So the end-to-end test can assert real
improvement -- validation climbing 0.0 -> 1.0, a genuine rejection in the
middle -- rather than a smoke signal.

It is deterministic by construction: every response is a pure function of the
request and the out-of-band ``context`` the agent passes alongside it. Two
runs in two empty directories produce byte-identical workspaces.

``context`` never reaches a real model. It is how this backend stands in for
the benchmark knowledge a real model would get from the environment.
"""

from __future__ import annotations

import json
import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from ..bench import starter
from .base import LLMRequest, LLMResponse


class MockBackend:
    name = "mock"

    def describe(self) -> dict[str, Any]:
        return {"backend": self.name, "deterministic": True}

    def complete(self, req: LLMRequest) -> LLMResponse:
        if req.role == "inference":
            text = _inference(req)
        elif req.role == "maintainer":
            text = _maintainer(req)
        elif req.role == "proposer":
            text = _proposer(req)
        else:
            text = ""
        return LLMResponse(text=text, model=req.model, usage={"input_tokens": 0, "output_tokens": 0})


#: What a skill has to *say* for the simulated agent to act on it.
#:
#: Each family lists groups of alternatives; every group must match somewhere
#: in the skill text. So `iso_z` needs the skill to name the standard *and*
#: the trailing Z -- mentioning only one is not a usable instruction.
#:
#: This is keyword recognition standing in for comprehension. It is a
#: simulation, and an honest one only if you know its limits: it rewards a
#: skill that states the rule unambiguously and rejects one that waffles,
#: but it cannot tell a well-written skill from a merely correct one. That
#: judgement needs a real model. It exists so tutorial exercises can be
#: graded offline, with no API key.
_PROSE_SIGNALS: dict[str, tuple[str, ...]] = {
    "iso_z": (r"iso[-\s]?8601", r"z|zulu|trailing\s+z"),
    "rec_prefix": (r"rec-", r"upper|canonical"),
    "page_two": (r"page\s*2|second\s+page|paginat|next\s+page",),
    "round_even": (r"half[-\s]?(to[-\s]?)?even|banker",),
    "idem_key": (r"idempotency[_\s-]?key", r"colon|:"),
}


def _knows(system: str, family: str) -> bool:
    """Does the injected skill set actually teach this family's rule?

    Two ways to satisfy it: the explicit marker (used by the mock maintainer
    and proposer inside the evolution loop) or prose that states the rule
    (used by humans writing skills by hand in the tutorials).
    """
    if starter.QUIRK_TOKEN.format(family=family) in system:
        return True
    body = system.lower()
    groups = _PROSE_SIGNALS.get(family)
    if not groups:
        return False
    return all(re.search(pattern, body) for pattern in groups)


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------


def covered_families(skill_text: str) -> list[str]:
    """Which families a body of skill text actually teaches.

    Exposed because the mock proposer has to agree with the mock inference
    agent about what is already covered. When they disagreed, the proposer
    kept re-proposing a family the skills already handled, every proposal
    was correctly rejected for not improving anything, and the run plateaued
    -- a loop that looked broken but was only mis-informed.
    """
    return [f for f in starter.FAMILIES if _knows(skill_text, f)]


def _inference(req: LLMRequest) -> str:
    family = req.context["family"]
    instance = int(req.context["instance"])
    turn = int(req.context.get("turn", 0))
    knows = _knows(req.system, family)

    if turn == 0:
        page = 2 if (family == "page_two" and knows) else 1
        query = starter._rid(family, instance).lower()
        return (
            f"THOUGHT: locate the record for {family}.\n"
            f'ACTION: search {{"query": "{query}", "page": {page}}}'
        )

    answer = starter._expected(family, instance) if knows else _wrong(family, instance)
    return (
        "THOUGHT: I have what I need.\n"
        f"ANSWER: {json.dumps(answer, sort_keys=True)}"
    )


def _wrong(family: str, instance: int) -> dict[str, Any]:
    """The plausible mistake each quirk provokes when the rule is unknown."""
    rid = starter._rid(family, instance)
    if family == "iso_z":
        return {"record_id": rid, "timestamp": starter._TIMESTAMPS[instance].replace(" ", "T")}
    if family == "rec_prefix":
        return {"record_id": rid, "status": "unknown"}
    if family == "page_two":
        return {"record_id": rid, "owner": f"decoy-{instance}0"}
    if family == "round_even":
        half_up = Decimal(starter._AMOUNTS[instance]).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return {"record_id": rid, "amount": float(half_up)}
    if family == "idem_key":
        return {"record_id": rid, "operation": "reconcile"}
    raise ValueError(family)


# ---------------------------------------------------------------------------
# Wiki maintenance
# ---------------------------------------------------------------------------

_RULES = {
    "iso_z": "Emit timestamps as ISO-8601 with a literal `T` separator and a trailing `Z`.",
    "rec_prefix": "`fetch` only accepts the canonical uppercase `REC-` id; search returns lowercase.",
    "page_two": "`search` paginates at three hits -- request page 2 before concluding.",
    "round_even": "Round money half-to-even at two decimals, not half-up.",
    "idem_key": 'Write payloads must include `idempotency_key` = "<record_id>:<operation>".',
}


def _maintainer(req: LLMRequest) -> str:
    """Document the worst undocumented failure family, patch-style."""
    failing: list[str] = list(req.context.get("failing_families", []))
    documented: set[str] = set(req.context.get("documented_families", []))
    evidence: dict[str, str] = dict(req.context.get("evidence", {}))

    target = next((f for f in failing if f not in documented), None)
    if target is None:
        return _fence({"edits": [], "log_entry": "No new failure modes this iteration."})

    traces = [evidence[target]] if target in evidence else []
    batch = {
        "edits": [
            {
                "op": "create_page",
                "path": f"patterns/{target.replace('_', '-')}.md",
                "title": f"Failure mode: {target}",
                "content": (
                    f"**Observed:** every `{target}` task fails the same way.\n\n"
                    f"**Root cause:** {_RULES[target]}\n\n"
                    f"**Workaround:** apply that rule before answering.\n\n"
                    f"**Marker:** {starter.QUIRK_TOKEN.format(family=target)}"
                ),
                "evidence_traces": traces,
            }
        ],
        "log_entry": f"Root-caused the `{target}` family and opened a pattern page for it.",
    }
    return _fence(batch)


# ---------------------------------------------------------------------------
# Skill proposal
# ---------------------------------------------------------------------------


def _proposer(req: LLMRequest) -> str:
    documented: list[str] = list(req.context.get("documented_families", []))
    covered: set[str] = set(req.context.get("covered_families", []))
    iteration = int(req.context.get("iteration", 1))
    decoy_at = req.context.get("decoy_iteration")

    target = next((f for f in documented if f not in covered), None)
    if target is None:
        return _fence(
            {
                "action": "edit",
                "target_skill": "records-service",
                "rationale": "Nothing new in the wiki to encode.",
                "evidence_patterns": [],
                "evidence_traces": [],
                "description": "House rules for the records service.",
                "body": "No change.",
                "purpose": "Placeholder.",
            },
            prefix="PROPOSAL:\n",
        )

    # One deliberately useless proposal, so the offline test exercises a real
    # rejection and a real rollback rather than only the happy path.
    is_decoy = decoy_at is not None and iteration == int(decoy_at)
    # The decoy must teach *nothing*. Merely restating the rule without the
    # marker is now enough for the agent to act on it, so a decoy that kept
    # the rule text would quietly succeed and the rejection path would stop
    # being exercised at all.
    marker = "" if is_decoy else starter.QUIRK_TOKEN.format(family=target)
    rule = (
        "Pay closer attention to this family and double-check the answer."
        if is_decoy
        else _RULES[target]
    )
    slug = target.replace("_", "-")
    page = f"patterns/{slug}.md"

    proposal = {
        "action": "create",
        "target_skill": f"handle-{slug}",
        "rationale": (
            f"The wiki documents `{target}` as a recurring failure; encode the rule."
            + (" (exploratory restatement, no new rule)" if is_decoy else "")
        ),
        "evidence_patterns": [page],
        "evidence_traces": [],
        "description": f"Apply the {target} rule when answering records-service tasks.",
        "body": f"## Rule\n\n{rule}\n\n{marker}".strip(),
        "purpose": f"Encodes the rule root-caused in `{page}`.",
    }
    return _fence(proposal, prefix="PROPOSAL:\n")


def _fence(obj: Any, prefix: str = "") -> str:
    return prefix + "```json\n" + json.dumps(obj, indent=2, sort_keys=True) + "\n```"
