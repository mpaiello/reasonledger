#!/usr/bin/env python3
"""
run_prompts.py — prompt-sensitivity experiment.

Runs the same clean + injected chains under each auditor prompt variant (prompts.py) and reports,
per prompt, the false-positive rate (on clean traces) and the detection rate (on injected errors).
Answers the decisive question: does prompt discipline fix the capable model's over-flagging without
killing detection?

Default: strong model, RL format (cheap and decisive). Widen with flags.

Usage:
  python run_prompts.py --mock            # offline wiring check (mock ignores prompt)
  python run_prompts.py                    # live; strong model, RL, 30 clean + 15 injected
  python run_prompts.py --formats=rl,json  # add JSON
  python run_prompts.py --both             # add the cheap model too
  python run_prompts.py 40                  # 40 clean chains
"""

import json
import random
import sys
from collections import defaultdict

from generate import generate_clean_chains
from inject import INJECTORS, ERROR_CLASSES
from render import RENDERERS
from score import score_trial, Tally
from prompts import PROMPTS
from audit import parse_auditor_response, mock_audit
import run_live


def build_trials(n_clean, n_inject_src):
    trials = [(c, None) for c in generate_clean_chains(n_clean, seed=0)]
    for c in generate_clean_chains(n_inject_src, seed=4242):
        for cls in ERROR_CLASSES:
            trials.append(INJECTORS[cls](c))
    return trials


def main():
    use_mock = "--mock" in sys.argv
    both = "--both" in sys.argv
    formats = ["rl"]
    for a in sys.argv:
        if a.startswith("--formats="):
            formats = a.split("=", 1)[1].split(",")
    n_clean = 30
    for a in sys.argv[1:]:
        if a.isdigit():
            n_clean = int(a)

    trials = build_trials(n_clean, 3)
    n_clean_t = sum(1 for _, gt in trials if gt is None)
    models = dict(run_live.MODELS) if both else {"strong": run_live.MODELS["strong"]}
    total = len(PROMPTS) * len(trials) * len(formats) * len(models)
    print(f"{n_clean_t} clean + {len(trials) - n_clean_t} injected; prompts={list(PROMPTS)}; "
          f"formats={formats}; models={list(models)}; ~{total} calls ({'MOCK' if use_mock else 'LIVE'})")

    out = {"config": {"prompts": list(PROMPTS), "formats": formats, "n_clean": n_clean_t,
                      "models": models}, "results": {}}
    for tier, model in models.items():
        tallies = defaultdict(Tally)
        for pname, tmpl in PROMPTS.items():
            for i, (chain, gt) in enumerate(trials):
                for fmt in formats:
                    trail = RENDERERS[fmt](chain)
                    if use_mock:
                        rng = random.Random(abs(hash((chain["chain_id"], fmt, i, pname))) % (2**32))
                        dets = mock_audit(trail, fmt, gt, rng)
                    else:
                        try:
                            dets = parse_auditor_response(
                                run_live.call_model(tmpl.format(trace=trail), model))
                        except Exception as e:
                            print(f"  ! {tier}/{pname}/{fmt} failed: {str(e).splitlines()[0][:50]}")
                            dets = []
                    tallies[(pname, fmt)].add(score_trial(dets, gt))

        print(f"\n[{tier}] {model}")
        print(f"{'prompt':10} {'format':6} {'detect':>7} {'false-pos':>10} {'n_inj':>6} {'n_clean':>8}")
        print("-" * 52)
        block = {}
        for pname in PROMPTS:
            for fmt in formats:
                t = tallies[(pname, fmt)]
                det, loc, fp = t.rates()
                print(f"{pname:10} {fmt:6} {det:7.2f} {fp:10.2f} {t.inj:6d} {t.clean:8d}")
                block[f"{pname}/{fmt}"] = {"detect": round(det, 3), "false_positive": round(fp, 3),
                                          "n_injected": t.inj, "n_clean": t.clean}
        out["results"][tier] = block

    if use_mock:
        print("\nMOCK proves wiring only: the mock ignores the prompt, so per-prompt rows match by design.")
        print("The real prompt effect needs the live run (drop --mock).")
        return
    with open("results_prompts.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote results_prompts.json")
    print("Read: does 'strict' (and 'precision') drop false-pos from the 'default' 1.00 while keeping detect high?")


if __name__ == "__main__":
    main()
