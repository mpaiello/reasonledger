"""
render.py — render one canonical chain into three information-matched formats.

All three carry the SAME fields (premises, constraints+basis, derivations+refs,
claims+status, verifications, trust). Only the format differs. That is what makes
the RL-vs-JSON comparison a fair test of the notation rather than of the information.
"""

import json


def _refs_prefix(step):
    return ("From " + ", ".join(step["refs"]) + ": ") if step.get("refs") else ""


def render_rl(chain):
    """Reasonledger notation. Hops are delimited by '=== hop N | from -> to | action ==='."""
    out = []
    for p in chain["premises"]:
        out.append(f"@FORMAL [{p['id']}]")
        out.append(p["text"])
        out.append("")
    for hop in chain["hops"]:
        out.append(f"=== hop {hop['n']} | {hop['frm']} -> {hop['to']} | {hop['action']} ===")
        out.append("")
        out.append(f"@PROVENANCE [hop_{hop['n']}]")
        out.append(f"  from: {hop['frm']}")
        out.append(f"  to: {hop['to']}")
        out.append(f"  action: {hop['action']}")
        out.append("")
        for con in hop["constraints"]:
            out.append(f"@LOGIC [{con['id']}] basis: {con['basis']}")
            out.append(con["text"])
            out.append("")
        for d in hop["derivations"]:
            out.append(f"@DERIVE [{d['id']}]")
            for s in d["steps"]:
                out.append(f"({s['n']}) {_refs_prefix(s)}{s['text']}")
            out.append(f"\u2192\u2192 {d['conclusion']}")
            out.append("")
        if hop["claims"]:
            out.append("@TAXONOMY [claims]")
            for cl in hop["claims"]:
                out.append(f"{cl['id']}: {cl['status']}")
            out.append("")
        for v in hop["verifications"]:
            out.append(f"@VERIFY [\u00a7{v['deriv']}]")
            for r in v["results"]:
                label = r["step"] if r["step"] != "conclusion" else "conclusion"
                if isinstance(label, int):
                    out.append(f"({label}): {r['result']}")
                else:
                    out.append(f"{label}: {r['result']}")
            out.append("")
        if hop["trust"]:
            out.append("@TRUST_TRANSFORMATION [trust]")
            for t in hop["trust"]:
                out.append(f"{t['item']}: {t['label']}")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_json(chain):
    """Information-matched JSON trace (the decisive baseline)."""
    trace = {
        "chain_id": chain["chain_id"],
        "domain": chain["domain"],
        "premises": chain["premises"],
        "hops": [
            {
                "n": h["n"], "from": h["frm"], "to": h["to"], "action": h["action"],
                "constraints": h["constraints"],
                "derivations": h["derivations"],
                "claims": h["claims"],
                "verifications": h["verifications"],
                "trust": h["trust"],
            }
            for h in chain["hops"]
        ],
    }
    return json.dumps(trace, indent=2)


def render_prose(chain):
    """Information-matched natural-language narration."""
    lines = []
    lines.append(f"Reasoning trace for chain '{chain['chain_id']}' (domain: {chain['domain']}).")
    prem = "; ".join(f"{p['id']} = {p['text']}" for p in chain["premises"])
    lines.append(f"Established premises: {prem}.")
    lines.append("")
    for h in chain["hops"]:
        lines.append(f"Hop {h['n']}: {h['frm']} handed off to {h['to']} (action: {h['action']}).")
        for con in h["constraints"]:
            lines.append(f"  Active constraint {con['id']} ({con['basis'].lower()}): {con['text']}.")
        for d in h["derivations"]:
            steps = " ".join(f"Step {s['n']}: {_refs_prefix(s)}{s['text']}." for s in d["steps"])
            lines.append(f"  Derivation {d['id']}: {steps} Concluding: {d['conclusion']}.")
        for v in h["verifications"]:
            res = ", ".join(f"step {r['step']} {r['result']}" for r in v["results"])
            lines.append(f"  Verification of {v['deriv']}: {res}.")
        if h["claims"]:
            cls = ", ".join(f"{cl['id']} is {cl['status']}" for cl in h["claims"])
            lines.append(f"  Claim status: {cls}.")
        if h["trust"]:
            tr = ", ".join(f"{t['item']} was {t['label']}" for t in h["trust"])
            lines.append(f"  Trust: {tr}.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


RENDERERS = {"rl": render_rl, "json": render_json, "prose": render_prose}


if __name__ == "__main__":
    from canonical import seed_chains
    ch = seed_chains()[0]
    for fmt, fn in RENDERERS.items():
        print(f"\n########## {fmt} ##########")
        print(fn(ch)[:600])
