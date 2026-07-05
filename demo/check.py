"""
check.py — the mechanical checker.

It parses a rendered artifact (RL or JSON) back into a common structure, then applies
five cross-hop consistency rules, emitting detections {error_class, hop, item}.

Prose is intentionally NOT mechanically checkable: check("...", "prose") returns [].
That asymmetry is part of the finding — structured formats (RL and JSON alike) support
mechanical audit; prose does not.

Clean chains propagate one state across hops, so the rules (which compare each hop to the
hop-1 baseline, plus absolute reference/verification checks) raise nothing on a clean chain.
"""

import json
import re

HEADER_RE = re.compile(r"^@(?P<type>[A-Z_]+)\b(?P<rest>.*)$")
LABEL_RE = re.compile(r"\[\s*(?P<label>[^\]]*?)\s*\]")
BASIS_RE = re.compile(r"\bbasis\s*:\s*(?P<v>\w+)", re.IGNORECASE)
STEP_RE = re.compile(r"^\((?P<n>\d+)\)\s*(?P<text>.*)$")
KV_RE = re.compile(r"^\s*(?P<k>[^:]+?)\s*:\s*(?P<v>.+?)\s*$")
REF_RE = re.compile(r"@[A-Z_]+\[\s*([^\]]+?)\s*\]|\u00a7([A-Za-z]\w*)")


# ---------- parsers ----------------------------------------------------------

def _split_blocks(lines):
    """Yield (type, label, rest, body_lines) for each @-block in a list of lines."""
    blocks, cur = [], None
    for raw in lines:
        m = HEADER_RE.match(raw)
        if m:
            lm = LABEL_RE.search(m.group("rest"))
            cur = [m.group("type"), (lm.group("label") if lm else None), m.group("rest"), []]
            blocks.append(cur)
        elif cur is not None and raw.strip():
            cur[3].append(raw)
    return blocks


def _parse_hop_blocks(blocks):
    hop = {"constraints": [], "derivations": [], "claims": [],
           "verifications": [], "trust": []}
    for btype, label, rest, body in blocks:
        if btype == "LOGIC":
            bm = BASIS_RE.search(rest)
            hop["constraints"].append({
                "id": label, "text": " ".join(b.strip() for b in body),
                "basis": bm.group("v") if bm else None})
        elif btype == "DERIVE":
            steps, conclusion = [], None
            for b in body:
                sm = STEP_RE.match(b.strip())
                if sm:
                    refs = ["".join(t) for t in REF_RE.findall(b)]
                    steps.append({"n": int(sm.group("n")), "text": sm.group("text"), "refs": refs})
                elif b.strip().startswith("\u2192\u2192"):
                    conclusion = b.strip()[2:].strip()
            hop["derivations"].append({"id": label, "steps": steps, "conclusion": conclusion})
        elif btype == "TAXONOMY":
            for b in body:
                kv = KV_RE.match(b)
                if kv:
                    hop["claims"].append({"id": kv.group("k"), "status": kv.group("v").strip()})
        elif btype == "VERIFY":
            deriv = (label or "").lstrip("\u00a7")
            results = []
            for b in body:
                kv = KV_RE.match(b)
                if kv:
                    key = kv.group("k").strip()
                    sm = re.match(r"^\((\d+)\)$", key)
                    step = int(sm.group(1)) if sm else key
                    results.append({"step": step, "result": kv.group("v").strip()})
            hop["verifications"].append({"deriv": deriv, "results": results})
        elif btype == "TRUST_TRANSFORMATION":
            for b in body:
                kv = KV_RE.match(b)
                if kv:
                    hop["trust"].append({"item": kv.group("k").strip(), "label": kv.group("v").strip()})
    return hop


def parse_rl(text):
    lines = text.splitlines()
    # global premises = @FORMAL blocks before the first hop delimiter
    hop_starts = [i for i, ln in enumerate(lines) if ln.startswith("=== hop")]
    head = lines[:hop_starts[0]] if hop_starts else lines
    premises = []
    for btype, label, rest, body in _split_blocks(head):
        if btype == "FORMAL":
            premises.append({"id": label, "text": " ".join(b.strip() for b in body)})
    hops = []
    for idx, start in enumerate(hop_starts):
        end = hop_starts[idx + 1] if idx + 1 < len(hop_starts) else len(lines)
        m = re.search(r"=== hop (\d+)", lines[start])
        n = int(m.group(1)) if m else idx + 1
        hop = _parse_hop_blocks(_split_blocks(lines[start + 1:end]))
        hop["n"] = n
        hops.append(hop)
    return {"premises": premises, "hops": hops}


def parse_json(text):
    d = json.loads(text)
    hops = []
    for h in d["hops"]:
        hops.append({
            "n": h["n"],
            "constraints": h.get("constraints", []),
            "derivations": h.get("derivations", []),
            "claims": h.get("claims", []),
            "verifications": h.get("verifications", []),
            "trust": h.get("trust", []),
        })
    return {"premises": d.get("premises", []), "hops": hops}


# ---------- consistency rules ------------------------------------------------

def _hop1(parsed):
    for h in parsed["hops"]:
        if h["n"] == 1:
            return h
    return parsed["hops"][0]


def _by_id(items, key="id"):
    return {it[key]: it for it in items}


def rules(parsed):
    detections = []
    base = _hop1(parsed)
    base_con = _by_id(base["constraints"])
    base_claim = _by_id(base["claims"])
    base_trust = _by_id(base["trust"], "item")

    defined_ids = set(p["id"] for p in parsed["premises"])
    for h in parsed["hops"]:
        defined_ids |= set(c["id"] for c in h["constraints"])
        defined_ids |= set(d["id"] for d in h["derivations"])

    for h in parsed["hops"]:
        if h["n"] != base["n"]:
            # R1 constraint drift (text differs from baseline)
            for c in h["constraints"]:
                if c["id"] in base_con and c["text"].strip() != base_con[c["id"]]["text"].strip():
                    detections.append({"error_class": "constraint_drift", "hop": h["n"], "item": c["id"]})
            # R2 status inflation (open -> confirmed vs baseline)
            for cl in h["claims"]:
                b = base_claim.get(cl["id"])
                if b and b["status"] != "confirmed" and cl["status"] == "confirmed":
                    detections.append({"error_class": "status_inflation", "hop": h["n"], "item": cl["id"]})
            # R3 trust laundering (trusted -> verified vs baseline)
            for t in h["trust"]:
                b = base_trust.get(t["item"])
                if b and b["label"] == "trusted" and t["label"] == "verified":
                    detections.append({"error_class": "trust_laundering", "hop": h["n"], "item": t["item"]})

        # R4 dangling reference (absolute)
        for d in h["derivations"]:
            for s in d["steps"]:
                for r in s.get("refs", []):
                    inner = re.sub(r"^@[A-Z_]+\[|\]$|^\u00a7", "", r).strip()
                    if inner and inner not in defined_ids:
                        detections.append({"error_class": "dangling_reference", "hop": h["n"], "item": d["id"]})

        # R5 verification inconsistency (a failure reported while a claim stays confirmed)
        confirmed = any(cl["status"] == "confirmed" for cl in h["claims"])
        for v in h["verifications"]:
            if confirmed and any(r["result"] == "fails" for r in v["results"]):
                detections.append({"error_class": "verification_inconsistency", "hop": h["n"], "item": v["deriv"]})

    # dedupe
    seen, uniq = set(), []
    for d in detections:
        k = (d["error_class"], d["hop"], d["item"])
        if k not in seen:
            seen.add(k)
            uniq.append(d)
    return uniq


def check(text, fmt):
    """Return mechanical detections for a rendered artifact. Prose is not checkable -> []."""
    if fmt == "rl":
        return rules(parse_rl(text))
    if fmt == "json":
        return rules(parse_json(text))
    return []  # prose: no mechanical checker


if __name__ == "__main__":
    from canonical import seed_chains
    from render import render_rl, render_json
    from inject import INJECTORS
    ch = seed_chains()[0]
    for name, fn in INJECTORS.items():
        corrupt, gt = fn(ch)
        dr = check(render_rl(corrupt), "rl")
        dj = check(render_json(corrupt), "json")
        print(f"{name:28s} gt={gt}")
        print(f"    rl  -> {dr}")
        print(f"    json-> {dj}")
