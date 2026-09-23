# Lesson 2 — Inference isolation

## The paper's key result

The ablation is in the paper itself: let the Inference Agent read the wiki,
and average performance on the benchmark drops from **63.7% to 60.9%**. Remove
the wiki entirely and it drops to **48.7%**.

The agent leans on raw material instead of distilled rules. The wiki is *more
information* in a literal sense, but noisier information — traces of failures,
the tentative paths the maintainer explored, the false starts. An agent smart
enough to use raw data for generalization is already smart enough to
overfit to it.

## How isolation is enforced

This repo enforces it **structurally, not by prompt**.

Open `src/wikiskill/agents/inference.py`. The signature is:

```python
class InferenceAgent:
    def __init__(self, backend: Backend, model: str, max_steps: int) -> None:
        self.backend = backend
        self.model = model
        self.max_steps = max_steps
```

Notice what is *not* there: no `wiki` parameter. The module does not import
`layers.wiki`. This is not a convention; it is a constraint.

Later, in `src/wikiskill/loop.py`, when the loop creates the Inference Agent,
it passes exactly those three things:

```python
self.inference = InferenceAgent(backend, inference_model, max_steps)
```

No wiki handle. Never. That is the guarantee.

And there is a test for it: `tests/test_no_wiki_leak.py`. Run it:

```bash
python -m unittest tests.test_no_wiki_leak
```

It scans the `inference.py` module for imports of `wiki` and for usages of
the word `wiki` in the source. If either is found, the test fails. Not because
we assume people are careless, but because a refactor can accidentally slip a
parameter in "for convenience" without anyone noticing it — especially if the
prompt says "do not read the wiki" and the refactor looks like it works.

## Why structural beats prompt

A prompt line like "ignore the wiki" lives in the face of the code. Someone
reading `InferenceAgent.__init__` sees fifteen parameters, five of which are
ignored, and they shrink from sight. A prompt instruction inside the docstring
is invisible the moment you look at a call site.

A structural guarantee survives the refactor. If the parameter does not exist,
it cannot be passed. If the module does not import the layer, a colleague
searching the codebase for "where does inference read the wiki?" finds nothing
because there is no path.

That matters because the constraint is not about this repository's discipline.
It is the mechanical enforcement of a finding: **do not expose this information
even if you think you should.** When the cost of breaking this invariant is
"rewrite the class signature", people think twice.

---

Next: [Lesson 3 — The gate](lesson-03-the-gate.md)
