"""Command line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .backends import BACKENDS
from .config import MODEL_INFERENCE, MODEL_MAINTAINER, MODEL_PROPOSER, RunConfig
from .loop import EvolutionLoop, Workspace
from .util import read_text_lf


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wikiskill", description=__doc__)
    p.add_argument("--workspace", type=Path, default=Path("workspace"))
    p.add_argument("--backend", choices=BACKENDS, default="claude-cli")
    p.add_argument("--inference-model", default=MODEL_INFERENCE)
    p.add_argument("--maintainer-model", default=MODEL_MAINTAINER)
    p.add_argument("--proposer-model", default=MODEL_PROPOSER)
    p.add_argument("--proposer-effort", default="high")
    p.add_argument("--gate-margin", type=float, default=0.0)
    p.add_argument("--max-steps", type=int, default=10)
    p.add_argument(
        "--skill-budget-bytes",
        type=int,
        default=8192,
        help="reject a proposal whose single skill exceeds this (default 8192)",
    )
    p.add_argument(
        "--skillset-budget-bytes",
        type=int,
        default=32768,
        help="reject a proposal that would take the whole set past this "
        "(default 32768). Skills only accumulate, so this is the only thing "
        "standing between you and a prompt made mostly of old advice.",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="parallel rollouts (default 4; use 1 to serialise)",
    )
    p.add_argument("--seed", type=int, default=0)
    p.add_argument(
        "--decoy-iteration",
        type=int,
        default=None,
        help="mock backend only: emit a deliberately useless proposal at this "
        "iteration, to exercise the rejection path",
    )

    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create the workspace and its three layers")
    sub.add_parser("status", help="show HEAD, R_best and the iteration history")

    b = sub.add_parser("baseline", help="score a split with no skills at all")
    b.add_argument("--split", default="val", choices=("train", "val", "test"))

    r = sub.add_parser("run", help="run the evolution loop")
    r.add_argument("-k", "--iterations", type=int, default=8)

    sub.add_parser("iterate", help="run exactly one iteration")

    e = sub.add_parser("eval", help="score a split under a chosen skill set")
    e.add_argument("--split", default="test", choices=("train", "val", "test"))
    e.add_argument("--skills", default="accepted", help="accepted | none | <sha>")
    e.add_argument(
        "--skills-dir",
        type=Path,
        default=None,
        help="score a hand-written folder of <name>/SKILL.md instead; "
        "overrides --skills. This is how you find out whether a skill you "
        "wrote yourself actually helped.",
    )

    s = sub.add_parser("show", help="print a workspace artifact")
    s.add_argument("what", choices=("wiki", "skills", "impact", "log"))

    sub.add_parser("report", help="baseline vs evolved summary")
    return p


def config_from(args: argparse.Namespace) -> RunConfig:
    extra = {}
    if args.decoy_iteration is not None:
        extra["decoy_iteration"] = str(args.decoy_iteration)
    return RunConfig(
        workspace=args.workspace,
        backend=args.backend,
        inference_model=args.inference_model,
        maintainer_model=args.maintainer_model,
        proposer_model=args.proposer_model,
        proposer_effort=args.proposer_effort,
        iterations=getattr(args, "iterations", 8),
        gate_margin=args.gate_margin,
        max_steps=args.max_steps,
        skill_budget_bytes=args.skill_budget_bytes,
        skillset_budget_bytes=args.skillset_budget_bytes,
        concurrency=args.concurrency,
        seed=args.seed,
        extra=extra,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = config_from(args)

    if args.command == "init":
        Workspace.open(cfg)
        print(f"workspace ready at {cfg.workspace}")
        print("  raw/     immutable traces")
        print("  wiki/    patterns, logs.md, skill-impact.md  (never rolled back)")
        print("  skills/  mirror of HEAD")
        return 0

    loop = EvolutionLoop(cfg)

    if args.command == "status":
        head = loop.ws.skills.head()
        print(f"HEAD   {head['sha']}  (iteration {head['iter']})")
        print(f"R_best {head['r_best']:.3f}")
        print(f"skills {', '.join(loop.ws.skills.head_skillset().names()) or '(none)'}")
        print(f"wiki   {len(loop.ws.wiki.pages())} pattern page(s)")
        for entry in loop.ws.journal.entries():
            if entry["phase"] == "gate_decision":
                verdict = "accept" if entry["data"].get("accepted") else "reject"
                print(f"  iter {entry['iter']}: {verdict}  R_best={entry['data'].get('r_best')}")
        return 0

    if args.command == "baseline":
        print(f"{args.split} baseline (no skills): {loop.baseline(args.split):.3f}")
        return 0

    if args.command in ("run", "iterate"):
        n = 1 if args.command == "iterate" else args.iterations
        results = loop.run(n)
        if not results:
            print("nothing to do (already converged or fully journaled)")
        for r in results:
            verdict = "ACCEPT" if r.accepted else f"REJECT ({r.reject_reason})"
            print(
                f"iter {r.iteration}: train={r.train_score:.2f} "
                f"val cand={r.val_candidate:.2f} inc={r.val_incumbent:.2f} "
                f"-> {verdict}  R_best={r.r_best_after:.2f}"
            )
        return 0

    if args.command == "eval":
        label = str(args.skills_dir) if args.skills_dir else args.skills
        score, traces = loop.evaluate(args.split, args.skills, args.skills_dir)
        print(f"{args.split} ({label}): {score:.3f} over {len(traces)} task(s)")
        failed = [t for t in traces if not t.passed]
        for t in failed:
            print(f"  FAIL {t.task_id:<16} {t.failure_summary or ''}")
        if not failed:
            print("  all tasks passed")
        return 0

    if args.command == "show":
        paths = cfg.paths
        target = {
            "wiki": paths.wiki_index,
            "impact": paths.skill_impact,
            "log": paths.logs,
        }.get(args.what)
        if args.what == "skills":
            for d in sorted(p for p in paths.skills.iterdir() if p.is_dir()):
                print(f"===== {d.name} =====")
                print(read_text_lf(d / "SKILL.md"))
            return 0
        if target is None or not target.exists():
            print(f"nothing at {target}")
            return 1
        print(read_text_lf(target))
        return 0

    if args.command == "report":
        base, _ = loop.evaluate("test", "none")
        evolved, _ = loop.evaluate("test", "accepted")
        head = loop.ws.skills.head()
        print("## WikiSkill run report\n")
        print(f"- held-out test, no skills:      {base:.3f}")
        print(f"- held-out test, evolved skills: {evolved:.3f}")
        print(f"- delta:                         {evolved - base:+.3f}")
        print(f"- skills at HEAD:                {', '.join(loop.ws.skills.head_skillset().names()) or '(none)'}")
        print(f"- wiki pattern pages:            {len(loop.ws.wiki.pages())}")
        print(f"- HEAD sha:                      {head['sha']}")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
