"""Calibration runner for specgate L6 (T16). Sequential, real `claude -p` calls."""

import json
import os
import re
import sys
import traceback
from pathlib import Path

W = Path("/mnt/media/local-storage/code/GitHub/harness-engineering-demo-wt")
CAL = W / "plugins/specgate/tests/fixtures/calibration"
EVID = W / ".specgate/evidence/T16"
sys.path.insert(0, str(W / "plugins/specgate/src"))

from specgate import cli  # noqa: E402
from specgate.l6_debate import run_debate  # noqa: E402


def build_change(fx: Path) -> str:
    parts = [f"Feature fixture: {fx.name}. Files (line-numbered):"]
    for rel in ["prd.md"] + sorted(
        str(p.relative_to(fx)) for p in fx.rglob("*.py") if "__pycache__" not in p.parts
    ):
        text = (fx / rel).read_text().splitlines()
        numbered = "\n".join(f"{i + 1:>3}| {ln}" for i, ln in enumerate(text))
        parts.append(f"=== {rel} ===\n{numbered}")
    parts.append(
        "Judge whether src genuinely implements every AC in prd.md (honouring the 'then' "
        "clause), tests genuinely test the AC they claim to cover, and no src code is "
        "unreachable from an AC. If you veto, cite file (path as shown, e.g. src/x.py), "
        "line (single integer) and a concrete claim."
    )
    return "\n\n".join(parts)


def make_recheck(fx: Path):
    def recheck(file: str, line: str, claim: str) -> bool:
        p = (fx / str(file)).resolve()
        if not str(file) or fx.resolve() not in p.parents or not p.is_file():
            return False
        m = re.match(r"\s*(\d+)", str(line))
        lines = p.read_text().splitlines()
        if not m or not (1 <= int(m.group(1)) <= len(lines)):
            return False
        n = int(m.group(1))
        window = " ".join(lines[max(0, n - 3): n + 2]).lower()
        toks = re.findall(r"[A-Za-z_]{4,}", str(claim).lower())
        return any(t in window for t in toks)

    return recheck


def earlier_layers(fx: Path) -> dict:
    for layer in range(0, 6):
        try:
            findings, red = cli.check_layer(layer, change_dir=str(fx))
        except Exception:
            return {"red_layer": layer,
                    "findings": [{"rule": "EXC", "message": traceback.format_exc()[-400:]}]}
        if red:
            return {"red_layer": layer, "findings": findings}
    return {"red_layer": None, "findings": []}


def main() -> None:
    env = os.environ.copy()
    token_shim = False
    if "CLAUDE_CODE_OAUTH_TOKEN" not in env and "ANTHROPIC_API_KEY" not in env:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = ""  # key-presence shim; claude uses its stored login
        token_shim = True
    out: dict = {"token_shim_used": token_shim, "fixtures": []}
    fxs = sorted(p for p in CAL.iterdir() if p.is_dir() and (p.name.startswith("good_") or p.name.startswith("bad_")))
    for fx in fxs:
        expected = "good" if fx.name.startswith("good_") else "bad"
        print(f"== {fx.name} ({expected})", flush=True)
        early = earlier_layers(fx)
        print(f"   earlier: red_layer={early['red_layer']}", flush=True)
        cdir = EVID / "cache" / fx.name
        res = run_debate(cdir, {"change": build_change(fx)}, make_recheck(fx), env=env)
        confirmed = [f for f in res["findings"] if f["rule"] == "SG603"]
        errors = [f for f in res["findings"] if f["rule"] in ("SG601", "SG602")]
        verdict = "veto" if confirmed else ("error" if errors else "pass")
        cf = cdir / "debate.cache.json"
        cache = json.loads(cf.read_text()) if cf.exists() else {}
        rec = {
            "fixture": fx.name,
            "expected": expected,
            "earlier_layers": early,
            "l6_panel_verdict": verdict,
            "l6_confirmed_vetoes": confirmed,
            "l6_ignored_vetoes": res["ignored_vetoes"],
            "l6_errors": errors,
            "l6_calls": res["calls"],
            "l6_cached_verdicts": [v["verdict"] for v in cache.values()],
        }
        rec["blocked"] = bool(early["red_layer"] is not None or confirmed or errors)
        out["fixtures"].append(rec)
        print(f"   L6={verdict} calls={res['calls']} blocked={rec['blocked']}", flush=True)
        EVID.mkdir(parents=True, exist_ok=True)
        (EVID / "calibration.partial.json").write_text(json.dumps(out, indent=1, sort_keys=True))

    bad = [r for r in out["fixtures"] if r["expected"] == "bad"]
    good = [r for r in out["fixtures"] if r["expected"] == "good"]
    out["summary"] = {
        "bad_total": len(bad),
        "bad_caught": sum(r["blocked"] for r in bad),
        "bad_caught_by_earlier_layer": sum(r["earlier_layers"]["red_layer"] is not None for r in bad),
        "bad_caught_by_l6_confirmed_veto": sum(bool(r["l6_confirmed_vetoes"]) for r in bad),
        "bad_missed": [r["fixture"] for r in bad if not r["blocked"]],
        "good_total": len(good),
        "good_wrongly_blocked": sum(r["blocked"] for r in good),
        "good_blocked_names": [r["fixture"] for r in good if r["blocked"]],
        "good_blocked_by_l6": [r["fixture"] for r in good if r["l6_confirmed_vetoes"] or r["l6_errors"]],
    }
    (EVID / "calibration.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    print(json.dumps(out["summary"], indent=1), flush=True)


if __name__ == "__main__":
    main()
