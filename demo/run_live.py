#!/usr/bin/env python3
"""
run_live.py — the live LLM-auditor arm (Phase 1, item 7). Runs on the Tirana laptop.

This is run_pilot.py with the mock auditor replaced by real model calls. It reuses the
tested modules (canonical, inject, render, check, score, visualize) unchanged.

SETUP (PowerShell, once per session):
  Set-PSReadLineOption -HistorySaveStyle SaveNothing
  $env:TOGETHER_API_KEY = "PASTE_YOUR_REAL_KEY_HERE"     # replace the placeholder; do not leave it
  pip install together

SMOKE TEST FIRST (one trail, prints the raw model reply so you can confirm parsing):
  python run_live.py --smoke

FULL RUN (writes results_live.json + a ledger view):
  python run_live.py            # 1 replicate (temp 0), N = chains x classes
  python run_live.py 3          # 3 replicates if you want more N at temperature > 0

The decisive contrast is RL vs information-matched JSON, reported per model tier. Read the gap
against the thresholds you locked in PHASE1_demo_preregistration.md.
"""

import json
import sys

from canonical import seed_chains
from inject import INJECTORS
from render import RENDERERS, render_rl
from check import check, parse_rl
from audit import live_audit, AUDITOR_PROMPT, parse_auditor_response
from score import score_trial, aggregate, format_table, decision
from visualize import render_html

# ---- EDIT THESE: confirm the model ids against Together's current catalog ---
MODELS = {
    "strong": "meta-llama/Llama-3.3-70B-Instruct-Turbo",   # verify current id
    "cheap":  "Qwen/Qwen2.5-7B-Instruct-Turbo",     # verify current id
}
TEMPERATURE = 0.0     # deterministic; raise (e.g. 0.5) only if you run replicates > 1
FORMATS = ["rl", "json", "prose"]

# ---- API wiring (Together.ai serverless) ------------------------------------
_client = None


def _get_client():
    global _client
    if _client is None:
        from together import Together
        _client = Together()   # reads TOGETHER_API_KEY from the environment
    return _client


def call_model(prompt, model, temperature=TEMPERATURE):
    r = _get_client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=800,
    )
    return r.choices[0].message.content or ""

# Anthropic alternative (uses ANTHROPIC_API_KEY, e.g. your v8Test key):
#   from anthropic import Anthropic
#   _acl = Anthropic()
#   def call_model(prompt, model, temperature=TEMPERATURE):
#       m = _acl.messages.create(model=model, max_tokens=800, temperature=temperature,
#                                messages=[{"role":"user","content":prompt}])
#       return "".join(b.text for b in m.content if b.type == "text")


# ---- smoke test -------------------------------------------------------------

def smoke():
    from inject import constraint_drift
    chain = seed_chains()[0]
    corrupt, gt = constraint_drift(chain)
    model = MODELS["cheap"]
    trail = render_rl(corrupt)
    print(f"# smoke: model={model}, injected={gt}\n")
    raw = call_model(AUDITOR_PROMPT.format(trace=trail), model)
    print("----- raw model reply -----")
    print(raw)
    print("----- parsed detections -----")
    print(parse_auditor_response(raw))
    print("\nIf the parsed list is empty but the reply clearly names the failure, the model")
    print("is not following the 'CLASS | HOP | ITEM' format. Adjust AUDITOR_PROMPT in audit.py")
    print("or the parser, then rerun --smoke before the full run.")


# ---- full run ---------------------------------------------------------------

def run(replicates):
    chains = seed_chains()
    per_model = {}
    for tier, model in MODELS.items():
        records = []
        n_calls = 0
        for chain in chains:
            for cls_name, injector in INJECTORS.items():
                for rep in range(replicates):
                    corrupt, gt = injector(chain)
                    for fmt in FORMATS:
                        trail = RENDERERS[fmt](corrupt)
                        # mechanical arm (deterministic, no API)
                        records.append({"format": fmt, "auditor": "mechanical",
                                        "score": score_trial(check(trail, fmt), gt)})
                        # live LLM arm
                        try:
                            dets = live_audit(trail, fmt, lambda p: call_model(p, model))
                            n_calls += 1
                        except Exception as e:
                            print(f"  ! call failed ({tier}/{fmt}/{cls_name}/{rep}): {e}")
                            dets = []
                        records.append({"format": fmt, "auditor": "llm",
                                        "score": score_trial(dets, gt)})
        per_model[tier] = (aggregate(records), n_calls)
        print(f"[{tier}] {model}: {n_calls} live calls\n")
        print(format_table(per_model[tier][0]))
        v, why = decision(per_model[tier][0])
        print(f"  decision ({tier}): {v} — {why}\n")
    return chains, per_model


def main():
    if "--smoke" in sys.argv:
        smoke()
        return
    replicates = 1
    for a in sys.argv[1:]:
        if a.isdigit():
            replicates = int(a)
    chains, per_model = run(replicates)

    out = {"config": {"models": MODELS, "temperature": TEMPERATURE,
                      "replicates": replicates, "chains": [c["chain_id"] for c in chains]},
           "results": {}}
    for tier, (tallies, n_calls) in per_model.items():
        block = {"n_calls": n_calls, "rates": {}}
        for (fmt, aud), t in tallies.items():
            det, loc, fp = t.rates()
            block["rates"][f"{fmt}/{aud}"] = {"detect": round(det, 3), "localize": round(loc, 3),
                                              "false_positive": round(fp, 3),
                                              "n_injected": t.inj, "n_clean": t.clean}
        v, why = decision(tallies)
        block["decision"] = {"verdict": v, "explanation": why}
        out["results"][tier] = block
    with open("results_live.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("wrote results_live.json")

    # ledger view for one injected RL trail (real artifact for the paper/venture)
    from inject import constraint_drift
    corrupt, gt = constraint_drift(chains[0])
    trail = render_rl(corrupt)
    html = render_html(parse_rl(trail), check(trail, "rl"),
                       title="Reasoning Ledger — audit view",
                       subtitle=f"chain '{chains[0]['chain_id']}' with injected {gt['error_class']} at hop {gt['hop']}")
    with open("ledger_view.html", "w") as fh:
        fh.write(html)
    print("wrote ledger_view.html")


if __name__ == "__main__":
    main()
