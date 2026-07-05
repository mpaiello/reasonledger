#!/usr/bin/env python3
"""
run_pilot.py — end-to-end pilot with the MOCK auditor.

Proves the whole pipeline: canonical chains -> inject -> render (3 formats) ->
mechanical check + auditor -> score -> DV tables + decision rule + a ledger view.

The auditor here is the MOCK (illustrative rates). To produce real results, swap
audit.audit(...) for audit.live_audit(..., call_model=...) on the Tirana laptop and
rerun. Nothing else changes.

Usage:  python run_pilot.py [replicates]
"""

import json
import random
import sys

from canonical import seed_chains
from inject import INJECTORS
from render import RENDERERS
from check import check, parse_rl
from audit import audit
from score import score_trial, aggregate, format_table, decision
from visualize import render_html

REPLICATES = int(sys.argv[1]) if len(sys.argv) > 1 else 10
FORMATS = ["rl", "json", "prose"]


def run(replicates=REPLICATES):
    chains = seed_chains()
    records = []
    for chain in chains:
        for cls_name, injector in INJECTORS.items():
            for rep in range(replicates):
                corrupt, gt = injector(chain)
                for fmt in FORMATS:
                    trail = RENDERERS[fmt](corrupt)
                    # mechanical checker (deterministic)
                    mech = check(trail, fmt)
                    records.append({"format": fmt, "auditor": "mechanical",
                                    "score": score_trial(mech, gt)})
                    # LLM auditor (mock), seeded per trial for realistic variance
                    seed = abs(hash((chain["chain_id"], cls_name, rep, fmt))) % (2**32)
                    rng = random.Random(seed)
                    llm = audit(trail, fmt, gt, rng)
                    records.append({"format": fmt, "auditor": "llm",
                                    "score": score_trial(llm, gt)})
    return chains, records


def main():
    chains, records = run()
    tallies = aggregate(records)

    print("=" * 62)
    print("Reasonledger Phase 1 pilot — MOCK auditor (illustrative, not empirical)")
    print(f"chains={len(chains)}  classes={len(INJECTORS)}  replicates={REPLICATES}  "
          f"trials/format={len(records)//len(FORMATS)//2}")
    print("=" * 62)
    print(format_table(tallies))
    print()

    verdict, why = decision(tallies)
    print(f"DECISION (mock, per locked rule): {verdict}")
    print(f"  {why}")
    print()
    print("Note: mechanical detection is equal for RL and JSON because both are structured and")
    print("parseable; prose is not mechanically checkable. On the mock LLM arm RL ~ JSON as well.")
    print("This is the honest pattern the design predicts; the live arm on the laptop is decisive.")

    # write results.json
    out = {"config": {"chains": [c["chain_id"] for c in chains],
                      "classes": list(INJECTORS.keys()),
                      "replicates": REPLICATES, "auditor": "MOCK"},
           "rates": {}}
    for (fmt, aud), t in tallies.items():
        det, loc, fp = t.rates()
        out["rates"][f"{fmt}/{aud}"] = {"detect": round(det, 3), "localize": round(loc, 3),
                                        "false_positive": round(fp, 3),
                                        "n_injected": t.inj, "n_clean": t.clean}
    out["decision_mock"] = {"verdict": verdict, "explanation": why}
    with open("results.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote results.json")

    # ledger view for one injected RL trail
    from inject import constraint_drift
    corrupt, gt = constraint_drift(chains[0])
    trail = render_rl_of(corrupt)
    parsed = parse_rl(trail)
    dets = check(trail, "rl")
    html = render_html(parsed, dets,
                       title="Reasoning Ledger — audit view",
                       subtitle=f"chain '{chains[0]['chain_id']}' with an injected {gt['error_class']} "
                                f"at hop {gt['hop']} (item '{gt['item']}')")
    with open("ledger_view.html", "w") as fh:
        fh.write(html)
    print("wrote ledger_view.html")


def render_rl_of(chain):
    from render import render_rl
    return render_rl(chain)


if __name__ == "__main__":
    main()
