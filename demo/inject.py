"""
inject.py — programmatic error injection with exact ground truth.

Each injector takes a clean canonical chain and returns (corrupted_chain, ground_truth),
where ground_truth is {"error_class","hop","item"} (or None for the clean control).
Injection targets a single hop (default: the last hop) so the failure is localizable.

The five classes each target a Reasonledger-designed detection point and are structurally
detectable by the mechanical checker (check.py):
  constraint_drift        - an active constraint's text mutates across hops
  status_inflation        - a claim goes open -> confirmed with no supporting verification
  trust_laundering        - a trust label goes trusted -> verified with no verification record
  dangling_reference      - a step references an undefined premise/constraint
  verification_inconsistency - a claim stays confirmed while its verification reports a failure
"""

import copy


def _target_hop(chain, hop_index):
    if hop_index is None:
        hop_index = len(chain["hops"]) - 1
    return hop_index, chain["hops"][hop_index]


def clean(chain, hop_index=None):
    return copy.deepcopy(chain), None


def constraint_drift(chain, hop_index=None):
    c = copy.deepcopy(chain)
    hi, hop = _target_hop(c, hop_index)
    con = hop["constraints"][0]
    # weaken "closed system" / add an unstated qualifier: the text no longer matches earlier hops
    con["text"] = con["text"].replace("closed system", "system").replace("closed", "")
    if con["text"] == chain["hops"][hi]["constraints"][0]["text"]:
        con["text"] = con["text"] + " (approximately)"
    return c, {"error_class": "constraint_drift", "hop": hi + 1, "item": con["id"]}


def status_inflation(chain, hop_index=None):
    c = copy.deepcopy(chain)
    hi, hop = _target_hop(c, hop_index)
    target = next((cl for cl in hop["claims"] if cl["status"] == "open"), None)
    if target is None:
        target = hop["claims"][0]
    target["status"] = "confirmed"  # upgraded with no supporting verification
    return c, {"error_class": "status_inflation", "hop": hi + 1, "item": target["id"]}


def trust_laundering(chain, hop_index=None):
    c = copy.deepcopy(chain)
    hi, hop = _target_hop(c, hop_index)
    target = next((t for t in hop["trust"] if t["label"] == "trusted"), None)
    if target is None:
        target = hop["trust"][0]
    target["label"] = "verified"  # laundered: no verification record exists for this item
    return c, {"error_class": "trust_laundering", "hop": hi + 1, "item": target["item"]}


def dangling_reference(chain, hop_index=None):
    c = copy.deepcopy(chain)
    hi, hop = _target_hop(c, hop_index)
    d = hop["derivations"][0]
    n = len(d["steps"]) + 1
    d["steps"].append({"n": n, "text": "invoke an auxiliary lemma", "refs": ["@FORMAL[ghost_lemma]"]})
    return c, {"error_class": "dangling_reference", "hop": hi + 1, "item": d["id"]}


def verification_inconsistency(chain, hop_index=None):
    c = copy.deepcopy(chain)
    hi, hop = _target_hop(c, hop_index)
    v = hop["verifications"][0]
    # flip a step to "fails" while the claim(s) supported by this derivation stay confirmed
    for r in v["results"]:
        if r["step"] != "conclusion":
            r["result"] = "fails"
            break
    return c, {"error_class": "verification_inconsistency", "hop": hi + 1, "item": v["deriv"]}


INJECTORS = {
    "clean": clean,
    "constraint_drift": constraint_drift,
    "status_inflation": status_inflation,
    "trust_laundering": trust_laundering,
    "dangling_reference": dangling_reference,
    "verification_inconsistency": verification_inconsistency,
}

ERROR_CLASSES = [k for k in INJECTORS if k != "clean"]


if __name__ == "__main__":
    from canonical import seed_chains
    chain = seed_chains()[0]
    for name, fn in INJECTORS.items():
        _, gt = fn(chain)
        print(f"{name:28s} -> {gt}")
