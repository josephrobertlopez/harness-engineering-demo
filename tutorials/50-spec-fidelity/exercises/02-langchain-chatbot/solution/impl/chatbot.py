"""SUP-88 help-centre chatbot: the LangChain wiring around policy.py.

    pip install langchain-core langchain-anthropic
    export ANTHROPIC_API_KEY=...
    python chatbot.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TextIO

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

import policy

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", policy.SYSTEM_TEMPLATE),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)


@dataclass(frozen=True, slots=True)
class Reply:
    text: str
    escalated: bool = False
    refused: bool = False


class HelpBot:
    def __init__(self, model: BaseChatModel, faq: list[policy.FaqEntry] | None = None):
        self.faq = faq if faq is not None else policy.load_faq()
        self.chain = PROMPT | model | StrOutputParser()
        self._sessions: dict[str, InMemoryChatMessageHistory] = {}

    def history(self, session_id: str) -> InMemoryChatMessageHistory:
        return self._sessions.setdefault(session_id, InMemoryChatMessageHistory())

    def reply(self, session_id: str, question: str) -> Reply:
        # Checked before anything else and never stored: a refused message
        # that reached the history would go to the model on the next turn.
        if policy.is_sensitive(question):
            return Reply(policy.REFUSAL, refused=True)

        history = self.history(session_id)
        entry = policy.retrieve(question, self.faq)
        if entry is None:
            text, escalated = policy.ESCALATION, True
        else:
            text = self.chain.invoke(
                {
                    "entry": entry.render(),
                    "history": policy.window(history.messages),
                    "question": question,
                }
            )
            escalated = False
        history.add_messages([HumanMessage(question), AIMessage(text)])
        return Reply(text, escalated=escalated)


def make_model() -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(**policy.model_params())


def run(bot: HelpBot, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> int:
    session = "terminal"
    stdout.write("Help centre. Ask a question; Ctrl-D (Ctrl-Z on Windows) to quit.\n")
    for line in stdin:
        question = line.strip()
        if not question:
            continue
        reply = bot.reply(session, question)
        tag = " [escalated]" if reply.escalated else ""
        stdout.write(f"bot{tag}: {reply.text}\n")
        stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(run(HelpBot(make_model())))
