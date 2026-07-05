"""
canonical.py — the format-agnostic representation of a multi-hop reasoning chain.

A chain is a dict:
  {
    "chain_id": str,
    "domain": str,
    "premises": [{"id","text"}],          # @FORMAL, global/stable
    "hops": [hop, ...]
  }
hop:
  {
    "n": int, "frm": str, "to": str, "action": str,
    "constraints":   [{"id","text","basis"}],            # @LOGIC (basis in AXIOM/DERIVED/EMPIRICAL)
    "derivations":   [{"id","steps":[{"n","text","refs"}],"conclusion"}],
    "claims":        [{"id","text","status"}],            # @TAXONOMY (confirmed/open/denied)
    "verifications": [{"deriv","results":[{"step","result"}]}],  # @VERIFY (holds/fails/uncertain)
    "trust":         [{"item","label"}]                   # label in {"verified","trusted"}
  }

A CLEAN chain propagates one base state identically across hops (only provenance changes),
so a correct mechanical checker finds nothing on it (zero false positives by construction).
Injectors (inject.py) corrupt a copy of one hop to create a known error.
"""

import copy


def _clean_chain(chain_id, domain, premises, base, models, actions):
    """Build an n-hop clean chain by propagating `base` state identically across hops."""
    hops = []
    for i in range(len(models) - 1):
        hop = {
            "n": i + 1,
            "frm": models[i],
            "to": models[i + 1],
            "action": actions[i],
            "constraints": copy.deepcopy(base["constraints"]),
            "derivations": copy.deepcopy(base["derivations"]),
            "claims": copy.deepcopy(base["claims"]),
            "verifications": copy.deepcopy(base["verifications"]),
            "trust": copy.deepcopy(base["trust"]),
        }
        hops.append(hop)
    return {"chain_id": chain_id, "domain": domain,
            "premises": copy.deepcopy(premises), "hops": hops}


def seed_chains():
    """Return a list of clean canonical chains covering distinct domains."""
    chains = []

    # ---- Seed 1: orbital mechanics ----
    premises = [
        {"id": "kepler_third", "text": "T^2 = (4*pi^2 / (G*M)) * a^3"},
        {"id": "newton_grav", "text": "F = G*m1*m2 / r^2"},
    ]
    base = {
        "constraints": [
            {"id": "energy", "text": "for any closed system S, d/dt E(S) = 0", "basis": "AXIOM"},
        ],
        "derivations": [
            {"id": "circular_velocity",
             "steps": [
                 {"n": 1, "text": "for a circular orbit gravity supplies the centripetal force", "refs": []},
                 {"n": 2, "text": "G*M*m / r^2 = m*v^2 / r", "refs": ["@FORMAL[newton_grav]"]},
                 {"n": 3, "text": "v^2 = G*M / r", "refs": []},
             ],
             "conclusion": "v = sqrt(G*M / r)"},
        ],
        "claims": [
            {"id": "bound_orbit", "text": "the orbit is gravitationally bound", "status": "confirmed"},
            {"id": "exact_eccentricity", "text": "the exact eccentricity is determined", "status": "open"},
            {"id": "parabolic_escape", "text": "the body escapes on a parabola", "status": "denied"},
        ],
        "verifications": [
            {"deriv": "circular_velocity",
             "results": [{"step": 1, "result": "holds"},
                         {"step": 2, "result": "holds"},
                         {"step": 3, "result": "holds"},
                         {"step": "conclusion", "result": "holds"}]},
        ],
        "trust": [
            {"item": "circular_velocity", "label": "verified"},
            {"item": "kepler_third", "label": "trusted"},
        ],
    }
    chains.append(_clean_chain(
        "orbital", "orbital_mechanics", premises, base,
        models=["model_A", "model_B", "model_C"],
        actions=["load+verify", "load+verify"]))

    # ---- Seed 2: propositional logic ----
    premises = [
        {"id": "modus_ponens", "text": "from P and (P -> Q), infer Q"},
        {"id": "given_p", "text": "P holds"},
    ]
    base = {
        "constraints": [
            {"id": "consistency", "text": "no proposition is both asserted and denied", "basis": "AXIOM"},
            {"id": "closure", "text": "only conclusions derived under active premises are asserted",
             "basis": "DERIVED"},
        ],
        "derivations": [
            {"id": "derive_q",
             "steps": [
                 {"n": 1, "text": "P holds", "refs": ["@FORMAL[given_p]"]},
                 {"n": 2, "text": "P -> Q is given", "refs": []},
                 {"n": 3, "text": "apply modus ponens to (1),(2)", "refs": ["@FORMAL[modus_ponens]"]},
             ],
             "conclusion": "Q holds"},
        ],
        "claims": [
            {"id": "q_true", "text": "Q holds", "status": "confirmed"},
            {"id": "r_status", "text": "R holds", "status": "open"},
        ],
        "verifications": [
            {"deriv": "derive_q",
             "results": [{"step": 1, "result": "holds"},
                         {"step": 2, "result": "holds"},
                         {"step": 3, "result": "holds"},
                         {"step": "conclusion", "result": "holds"}]},
        ],
        "trust": [
            {"item": "derive_q", "label": "verified"},
            {"item": "modus_ponens", "label": "trusted"},
        ],
    }
    chains.append(_clean_chain(
        "logic", "propositional_logic", premises, base,
        models=["model_A", "model_B", "model_C"],
        actions=["load+verify", "load+verify"]))

    return chains


if __name__ == "__main__":
    import json
    cs = seed_chains()
    print(f"{len(cs)} seed chains")
    for c in cs:
        print(f"  {c['chain_id']}: {len(c['hops'])} hops, "
              f"{len(c['premises'])} premises, "
              f"{len(c['hops'][0]['claims'])} claims")
    # dump one for inspection
    print(json.dumps(cs[0], indent=2)[:400])
