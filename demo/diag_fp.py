#!/usr/bin/env python3
"""
diag_fp.py — inspect WHAT the auditor flags on CLEAN traces.

FP=1.00 on clean chains could be (a) true hallucination (inventing failures that are not there)
or (b) flagging legitimate epistemic markers (open claims, trusted-but-unverified items) that the
scoring counts as false positives. These are different papers. This dumps the raw auditor reply on
a few clean chains next to the actual claim statuses and trust labels, so you can see which it is.

Also useful for the parsing caveat: it shows the raw text, so you can judge whether prose replies
would parse as reliably as structured ones.

Run:  python diag_fp.py         # 5 clean chains, RL, strong model
      python diag_fp.py 8       # 8 clean chains
"""

import sys
from generate import generate_clean_chains
from render import render_rl
from audit import AUDITOR_PROMPT, parse_auditor_response
import run_live


def main():
    n = 5
    for a in sys.argv[1:]:
        if a.isdigit():
            n = int(a)
    model = run_live.MODELS["strong"]
    print(f"# inspecting {n} CLEAN chains on {model} (RL)\n")
    for c in generate_clean_chains(n, seed=0):
        trail = render_rl(c)
        try:
            raw = run_live.call_model(AUDITOR_PROMPT.format(trace=trail), model)
        except Exception as e:
            print(f"call failed: {str(e).splitlines()[0][:70]}")
            continue
        claims = {x["id"]: x["status"] for x in c["hops"][0]["claims"]}
        trust = {x["item"]: x["label"] for x in c["hops"][0]["trust"]}
        print(f"===== CLEAN {c['chain_id']} ({c['domain']}) =====")
        print(f"  actual claims: {claims}")
        print(f"  actual trust : {trust}")
        print("  --- auditor raw reply ---")
        print(raw)
        print("  --- parsed as false positives ---")
        print(parse_auditor_response(raw))
        print()


if __name__ == "__main__":
    main()
