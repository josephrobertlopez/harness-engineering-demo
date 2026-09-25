"""Every decision SUP-88 makes, with no LangChain import.

Spec: openspec/changes/add-help-chat/specs/help-chat/spec.md

Kept stdlib-only so the rules the PRD cares about -- what is refused, what
escalates, how much is remembered, which model -- are testable on a machine
with nothing installed. `chatbot.py` only wires these into a chain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

FAQ_PATH = Path(__file__).with_name("faq.md")

ESCALATION = "I don't know that one yet — I've passed your question to a human."
REFUSAL = "I can't help with passwords or card numbers here. Please contact support@example.com."
HISTORY_LIMIT = 6

MODEL_ID = "claude-sonnet-5"
MAX_TOKENS = 512

SYSTEM_TEMPLATE = (
    "You are the help-centre assistant. Answer the customer using ONLY the "
    "FAQ entry below. If the entry does not answer their question, say you "
    "will pass it to a human. Do not invent policies, prices or time limits.\n\n"
    "FAQ entry:\n{entry}"
)

# 13-19 digits, each optionally followed by one space or dash. Bounded by
# non-digits so an order number glued to other digits is not a match.
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_SHARED_PASSWORD = re.compile(r"\b(password|passcode|pwd)\s*(is|:|=)\s*\S+", re.IGNORECASE)
_WORD = re.compile(r"[a-z][a-z-]*")


@dataclass(frozen=True, slots=True)
class FaqEntry:
    question: str
    keywords: frozenset[str]
    answer: str

    def render(self) -> str:
        return f"Q: {self.question}\nA: {self.answer}"


def load_faq(path: Path = FAQ_PATH) -> list[FaqEntry]:
    text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    entries: list[FaqEntry] = []
    for block in text.split("\n## ")[1:]:
        question, _, rest = block.partition("\n")
        keywords: frozenset[str] = frozenset()
        answer_lines = []
        for line in rest.strip().splitlines():
            if line.startswith("keywords:"):
                keywords = frozenset(k.strip().lower() for k in line[9:].split(",") if k.strip())
            else:
                answer_lines.append(line)
        entries.append(FaqEntry(question.strip(), keywords, "\n".join(answer_lines).strip()))
    return entries


def retrieve(question: str, faq: list[FaqEntry]) -> FaqEntry | None:
    words = set(_WORD.findall(question.lower()))
    best, best_hits = None, 0
    for entry in faq:
        hits = len(words & entry.keywords)
        # Strictly greater: ties keep the earlier entry, so the answer does
        # not depend on set iteration order.
        if hits > best_hits:
            best, best_hits = entry, hits
    return best


def is_sensitive(message: str) -> bool:
    return bool(_CARD.search(message) or _SHARED_PASSWORD.search(message))


def window(messages: list, limit: int = HISTORY_LIMIT) -> list:
    return list(messages[-limit:]) if limit > 0 else []


def model_params() -> dict:
    # No temperature: claude-sonnet-5 rejects it with a 400. No api_key: the
    # SDK reads ANTHROPIC_API_KEY (or another configured credential) itself.
    return {"model": MODEL_ID, "max_tokens": MAX_TOKENS}
