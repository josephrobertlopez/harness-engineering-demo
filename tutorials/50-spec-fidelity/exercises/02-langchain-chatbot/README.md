# Exercise 2 — SUP-88: a LangChain help-centre chatbot

**~60 minutes.** You get [`ticket.md`](ticket.md) and its attachment
[`faq.md`](faq.md). You hand in `prd.md`, `openspec/changes/<id>/` and
`impl/` — a LangChain chatbot on Claude that answers from the FAQ, hands
everything else to a human, remembers the conversation, and keeps card
numbers and passwords away from the model.

The step up from exercise 1: here the vague words hide **safety
properties**, and each one has a cheap fake that looks like a fix. "Not say
anything bad" is easy to "solve" with one line in a system prompt. That
line does not stop a card number being sent to a third party.

| file | what it is | Claude sees it? |
|---|---|---|
| `ticket.md`, `faq.md` | the ticket and its attachment | yes |
| `stakeholder-answers.md` | what the support lead says when asked | **no** — you are the support lead |
| `rubric.json`, `HARNESS.md` | what the judges check | yes |
| `solution/` | the reference answer | **no** — until you are done |

## Work backwards first (15 min)

```bash
python tutorials/50-spec-fidelity/start.py 02 ~/fidelity/backwards-02 --with-solution
python tutorials/50-spec-fidelity/spec_fidelity.py ~/fidelity/backwards-02
```

Without LangChain installed, the build stage fails with `not exercised
(skipped): 9 scenario(s) ...` -- every chain scenario, including all the
safety ones, was skipped. That is the judge being honest: a skipped test
has proved nothing. Install LangChain (below) and run it again, or pass
`--allow-skips` to see the rest of the report while you do.

Now walk these threads backwards, test → scenario → requirement → PRD →
answer → ticket:

1. `test_refused_not_remembered`. Which ticket phrase did it come from? Why
   is "not remembered" a separate requirement from "refused"? (Hint: what
   would the *next* turn send to the model?)
2. `test_uncovered_question` asserts `calls == []`. Why does the PRD care
   that the model is *not called*, not just that the reply is right?
3. `test_model_params`. Find the stakeholder answer, then find the row in
   this repo's [`CLAUDE.md`](../../../../CLAUDE.md) model table that
   explains why `temperature` must be absent.

Then look at the file split. `policy.py` imports nothing from LangChain.
`chatbot.py` is only wiring. The design says why — find the sentence.

## Then forward (45 min)

```bash
python tutorials/50-spec-fidelity/start.py 02 ~/fidelity/sup-88
cd ~/fidelity/sup-88 && claude
```

Follow [lesson 3](../../lesson-03-the-loop.md). Install LangChain in the
workspace before step 4:

```bash
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install langchain-core langchain-anthropic
```

Run the judge with that environment's `python`. It runs your tests with the
interpreter that runs it, so under a Python without LangChain the chain
tests skip and the report says so.

### Hints for this ticket

- **"Remember stuff"** — ask *how much*, *for how long*, and *shared between
  whom*. Each is a separate requirement with a separate test.
- **"Not say anything bad"** — ask what support is actually afraid of. The
  answer is not about tone.
- **"Smart about what it doesn't know"** — ask what happens instead of an
  answer, and whether the model is involved at all.
- **"Use Claude"** — ask for the exact model id and settings. Then check
  them against what the API accepts; one setting you might add by habit
  will return a 400.

### Test without an API key

Chain tests use LangChain's `FakeListChatModel`, behind a
`RunnableLambda` that records every prompt the model *would* have
received. That recorder is what lets a test assert "the refused message is
not in the history sent to the model", which is the property that matters:

```python
calls = []
def record(prompt_value):
    calls.append(prompt_value.to_messages())
    return prompt_value

model = RunnableLambda(record) | FakeListChatModel(responses=["..."])
bot = HelpBot(model)
```

### Run it for real

```bash
export ANTHROPIC_API_KEY=...          # or any credential the SDK resolves
cd impl && python chatbot.py
> I forgot my login, how do I reset it?
> my card is 4111 1111 1111 1111      # refused; never reaches the model
> what is the office dog called?      # escalated; no model call
```

Checked against `langchain-core` 1.6 and `langchain-anthropic` 1.7: the
request `ChatAnthropic(model="claude-sonnet-5", max_tokens=512)` sends
contains exactly `model`, `max_tokens` and `messages`, with no
`temperature`.

## Traps in this exercise

**Guarding in the prompt.** "Never repeat card numbers" in the system
prompt still *sends* the card number. The check has to run before the
chain is invoked. The `Spec captures intent` constraint in `HARNESS.md`
asks the enforcer to look for exactly this.

**Refusing, then remembering.** If the refused message is added to the
history, the next ordinary question sends it to the model anyway. Two
requirements, two tests.

**Refusing too much.** "I forgot my password" and "my password is not
working" are the most common help questions there are. The first
reference solution refused the second one, and every 16-digit order
number too -- an adversarial review caught both. The product owner's rule
is now exact (a card number must pass the Luhn check; a shared password is
one word containing a digit or symbol), and each false alarm is a
scenario of its own.

**Model id with a date suffix.** The id is complete as written:
`claude-sonnet-5`. `rubric.json` rejects `claude-sonnet-5-<date>`.

**Treating skipped tests as passed.** On a machine without LangChain, 9 of
18 tests skip. The judge reports every skipped scenario by name and fails
the build stage unless you pass `--allow-skips`. The repo's own CI passes
it, because CI has no LangChain -- which means CI proves the chain
scenarios are *tagged*, not that they pass. Run with LangChain installed
before you call it done.

## Resources

- LangChain: [models](https://docs.langchain.com/oss/python/langchain/models),
  [messages](https://docs.langchain.com/oss/python/langchain/messages),
  [short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory),
  [`ChatAnthropic`](https://docs.langchain.com/oss/python/integrations/chat/anthropic)
  — the docs now live on `docs.langchain.com`; many `python.langchain.com`
  links in older posts point at retired pages
- Claude: [models overview](https://docs.claude.com/en/docs/about-claude/models/overview)
- OpenSpec: [concepts](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md)
- Habitat-Thinking: [habitat engineering](https://habitat-thinking.github.io/ai-literacy-superpowers/plugins/ai-literacy-superpowers/explanation/habitat-engineering/),
  [three enforcement loops](https://habitat-thinking.github.io/ai-literacy-superpowers/plugins/ai-literacy-superpowers/explanation/three-enforcement-loops/)

## Checking your work

```bash
python tutorials/50-spec-fidelity/spec_fidelity.py ~/fidelity/sup-88
python tutorials/check.py 50-spec-fidelity/02     # grades this folder, if you copy your work here
```
