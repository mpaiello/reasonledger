#!/usr/bin/env python3
"""
diag.py — calibration check before the full run.

Runs each injected error class once through each model, RL format only, and prints whether
the auditor detected it plus the first line of its raw reply. ~10 cheap calls. Tells you if
the reading-auditor task is detectable at all (and whether the strong model beats the weak one)
before you spend on the full 3-format matrix.

Run:  python diag.py
"""

from canonical import seed_chains
from inject import INJECTORS, ERROR_CLASSES
from render import render_rl
from audit import AUDITOR_PROMPT, parse_auditor_response
import run_live  # reuse MODELS and call_model


def main():
    chain = seed_chains()[0]
    for tier, model in run_live.MODELS.items():
        print(f"\n===== {tier}: {model} =====")
        detected_count = 0
        for cls in ERROR_CLASSES:
            corrupt, gt = INJECTORS[cls](chain)
            trail = render_rl(corrupt)
            try:
                raw = run_live.call_model(AUDITOR_PROMPT.format(trace=trail), model)
            except Exception as e:
                print(f"  {cls:26s} CALL FAILED: {str(e).splitlines()[0][:70]}")
                continue
            dets = parse_auditor_response(raw)
            hit = any(d.get("error_class") == gt["error_class"] for d in dets)
            detected_count += 1 if hit else 0
            firstline = raw.strip().splitlines()[0][:70] if raw.strip() else "(empty)"
            print(f"  {cls:26s} detected={str(hit):5s} parsed={len(dets)}  raw: {firstline}")
        print(f"  -> {detected_count}/{len(ERROR_CLASSES)} classes detected in RL")


if __name__ == "__main__":
    main()
