"""Run configuration, workspace paths and model defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Models
#
# Model IDs are complete as written -- do not append date suffixes.
# Capability differences that the backends must respect:
#
#   claude-opus-5 / claude-sonnet-5
#       thinking: {"type": "adaptive"}, depth via output_config.effort.
#       temperature / top_p / top_k are REMOVED and return HTTP 400.
#   claude-haiku-4-5
#       thinking: {"type": "enabled", "budget_tokens": N}; `effort` errors.
#       sampling parameters are still accepted.
# ---------------------------------------------------------------------------

MODEL_INFERENCE = "claude-haiku-4-5"
MODEL_MAINTAINER = "claude-sonnet-5"
MODEL_PROPOSER = "claude-opus-5"


@dataclass(frozen=True, slots=True)
class ModelCaps:
    thinking: str  # "adaptive" | "budget"
    supports_effort: bool
    supports_sampling: bool


MODEL_CAPS: dict[str, ModelCaps] = {
    "claude-opus-5": ModelCaps("adaptive", True, False),
    "claude-opus-5-5": ModelCaps("adaptive", True, False),
    "claude-sonnet-5": ModelCaps("adaptive", True, False),
    "claude-haiku-4-5": ModelCaps("budget", False, True),
}


def caps_for(model: str) -> ModelCaps:
    """Capabilities for a model id, defaulting to the conservative shape.

    An unknown id is assumed adaptive-with-effort, which is the current-
    generation default; it is better to send the modern shape and get a clear
    400 than to silently send `temperature` to a model that rejects it.
    """
    return MODEL_CAPS.get(model, ModelCaps("adaptive", True, False))


# ---------------------------------------------------------------------------
# Workspace layout
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Paths:
    """The three persistent layers, plus harness-private bookkeeping.

    ``raw``, ``wiki`` and ``skills`` are the paper's layers. ``state`` is not:
    it holds the iteration journal and the content-addressed skill snapshots
    that make rollback and resume possible.
    """

    root: Path

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def wiki(self) -> Path:
        return self.root / "wiki"

    @property
    def patterns(self) -> Path:
        return self.wiki / "patterns"

    @property
    def logs(self) -> Path:
        return self.wiki / "logs.md"

    @property
    def skill_impact(self) -> Path:
        return self.wiki / "skill-impact.md"

    @property
    def wiki_index(self) -> Path:
        return self.wiki / "index.md"

    @property
    def skills(self) -> Path:
        """Human-readable mirror of HEAD. Nothing in the harness reads it."""
        return self.root / "skills"

    @property
    def state(self) -> Path:
        return self.root / ".state"

    @property
    def head(self) -> Path:
        return self.state / "HEAD.json"

    @property
    def journal(self) -> Path:
        return self.state / "journal.jsonl"

    @property
    def snapshots(self) -> Path:
        return self.state / "skillsets"

    @property
    def manifest(self) -> Path:
        return self.root / "manifest.json"

    def iter_dir(self, iteration: int) -> Path:
        return self.state / f"iter-{iteration:02d}"


@dataclass(frozen=True, slots=True)
class RunConfig:
    workspace: Path
    backend: str = "claude-cli"
    inference_model: str = MODEL_INFERENCE
    maintainer_model: str = MODEL_MAINTAINER
    proposer_model: str = MODEL_PROPOSER
    proposer_effort: str = "high"
    iterations: int = 8
    early_stop_score: float = 1.0
    gate_margin: float = 0.0
    """Candidate must beat the incumbent by strictly more than this.

    0.0 reproduces the paper's Eq. 4 exactly. On a 5-task validation split one
    task is a 20-point swing, so a small positive margin is the conservative
    setting -- a rejected good proposal costs one iteration, an accepted bad
    one poisons every proposal built on top of it.
    """
    max_steps: int = 10
    skill_budget_bytes: int = 8_192
    skillset_budget_bytes: int = 32_768
    proposer_max_reads: int = 8
    concurrency: int = 4
    """Parallel rollouts.

    Rollouts are independent -- a fresh environment per task, per-task trace
    files, a content-addressed response cache -- so this is close to linear
    speedup. Keep it modest: each `claude-cli` rollout spawns a ~237MB
    subprocess, and the account has rate limits.
    """
    seed: int = 0
    bench: str = "starter"
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def paths(self) -> Paths:
        return Paths(self.workspace)
