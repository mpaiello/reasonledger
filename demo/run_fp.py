#!/usr/bin/env python3
"""
run_fp.py — false-positive-focused rerun. Firms up the LLM-auditor false-positive rate with
real N by generating many varied CLEAN chains (plus a small injected set for detection context)
and reporting the false-positive rate per format per model.

This is a FOLLOW-UP to the pre-registered run in run_live.py, not part of the locked
pre-registration. It targets one open question: does the capable model's false-positive rate
on clean traces hold up beyond the original two clean trials?

Usage:
  python run_fp.py --mock     # offline sanity with the mock auditor (no API, instant)
  python run_fp.py            # live; default 30 clean chains + 3 injected-source chains
  python run_fp.py 40         # 40 clean chains

Reads MODELS from run_live.py (already configured). Live cost is a couple of dollars at most.
"""

import json
import random
import sys

from generate import generate_clean_chains
from inject import INJECTORS, ERROR_CLASSES
from render import RENDERERS
from check import check
from score import score_trial, aggregate, format_table
import run_live
from audit import live_audit, mock_audit

FORMATS = ["rl", "json", "prose"]


def build_trials(n_clean, n_inject_src):
    trials = [(c, None) for c in generate_clean_chains(n_clean, seed=0)]
    for c in generate_clean_chains(n_inject_src, seed=4242):
        for cls in ERROR_CLASSES:
            trials.append(INJECTORS[cls](c))
    return trials


def run(n_clean, n_inject_src, use_mock):
    trials = build_trials(n_clean, n_inject_src)
    n_clean_trials = sum(1 for _, gt in trials if gt is None)
    print(f"trials: {n_clean_trials} clean + {len(trials) - n_clean_trials} injected; "
          f"~{len(trials) * len(FORMATS)} auditor calls per model "
          f"({'MOCK' if use_mock else 'LIVE'})")
    per_model = {}
    for tier, model in run_live.MODELS.items():
        records = []
        for i, (chain, gt) in enumerate(trials):
            for fmt in FORMATS:
                trail = RENDERERS[fmt](chain)
                records.append({"format": fmt, "auditor": "mechanical",
                                "score": score_trial(check(trail, fmt), gt)})
                if use_mock:
                    rng = random.Random(abs(hash((chain["chain_id"], fmt, i))) % (2**32))
                    dets = mock_audit(trail, fmt, gt, rng)
                else:
                    try:
                        dets = live_audit(trail, fmt, lambda p: run_live.call_model(p, model))
                    except Exception as e:
                        print(f"  ! {tier}/{fmt} call failed: {str(e).splitlines()[0][:60]}")
                        dets = []
                records.append({"format": fmt, "auditor": "llm",
                                "score": score_trial(dets, gt)})
        per_model[tier] = aggregate(records)
        print(f"\n[{tier}] {model}")
        print(format_table(per_model[tier]))
        print("  -- LLM false-positive rate on CLEAN traces (the headline) --")
        for fmt in FORMATS:
            t = per_model[tier].get((fmt, "llm"))
            if t:
                _, _, fp = t.rates()
                print(f"     {fmt:6}: {fp:.2f}   (clean n={t.clean})")
        if use_mock:
            break  # mock: one model is enough to prove the wiring
    return per_model


def main():
    use_mock = "--mock" in sys.argv
    n_clean = 30
    for a in sys.argv[1:]:
        if a.isdigit():
            n_clean = int(a)
    per_model = run(n_clean, 3, use_mock)
    if use_mock:
        print("\nMOCK dry-run OK — wiring proven. Remove --mock to run live.")
        return
    out = {"config": {"models": run_live.MODELS, "n_clean": n_clean}, "results": {}}
    for tier, tallies in per_model.items():
        block = {}
        for (fmt, aud), t in tallies.items():
            det, loc, fp = t.rates()
            block[f"{fmt}/{aud}"] = {"detect": round(det, 3), "localize": round(loc, 3),
                                     "false_positive": round(fp, 3),
                                     "n_injected": t.inj, "n_clean": t.clean}
        out["results"][tier] = block
    with open("results_fp.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote results_fp.json")


if __name__ == "__main__":
    main()
