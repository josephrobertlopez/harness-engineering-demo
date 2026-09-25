# Track 50 exercises

Three builds, each from a deliberately vague Jira ticket. Start with
[the track README](../README.md) and [lesson 4](../lesson-04-work-backwards.md).

| exercise | ticket | you build |
|---|---|---|
| [01-docker-rest](01-docker-rest/README.md) | OPS-1432 | a Dockerised REST currency-conversion function |
| [02-langchain-chatbot](02-langchain-chatbot/README.md) | SUP-88 | a LangChain help-centre chatbot on Claude |
| [03-mcp-cli-tools](03-mcp-cli-tools/README.md) | DEVX-311 | a stdio MCP server over read-only `git` and `rg` tools |

## What is in each folder, and who may see it

| file | purpose | copied into your workspace? |
|---|---|---|
| `ticket.md` | the ticket, as filed | yes |
| `faq.md` | exercise 2's attachment | yes |
| `HARNESS.md` | how the work is judged, for the harness-enforcer | yes, paths rewritten |
| `stakeholder-answers.md` | what the product owner says when asked | **next to** the workspace, not in it: you are the product owner |
| `rubric.json` | the deterministic judge's facts and rules | **no**: its facts are the product owner's answers |
| `check.py` | grades this folder for `tutorials/check.py` | no |
| `solution/` | the reference answer | no, unless you ask for it with `--with-solution` |

Do the work in a workspace outside the repo, so Claude cannot read the
answers:

```bash
python tutorials/50-spec-fidelity/setup.py            # all three, in ~/fidelity
python tutorials/50-spec-fidelity/start.py 01 ~/fidelity/ops-1432
```

Editing a rubric? Every fact needs `examples` it accepts and
`counterexamples` it rejects where wording could flip its meaning, and must
not already be stated in the ticket. `tests/test_spec_fidelity.py`
enforces all of that.
