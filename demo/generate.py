"""
generate.py — procedurally generate many varied CLEAN chains.

The false-positive question needs real N. This builds structurally- and surface-varied clean
chains across several neutral domains, varying the claim-status mix (confirmed/open/denied) and
trust composition (verified/trusted) — the surfaces most likely to tempt an LLM auditor into
flagging a nonexistent failure. Every generated chain propagates one base state statically
across hops, so the mechanical checker finds nothing on it (genuinely clean by construction);
any LLM-auditor detection on these chains is therefore a false positive.

generate_clean_chains(n, seed) -> list of canonical chains (same schema as canonical.seed_chains()).
"""

import copy
import random

# Each derivation lists the premise ids it needs; those are always included so no ref dangles.
DOMAINS = {
    "orbital_mechanics": {
        "premises": {
            "kepler_third": "T^2 = (4*pi^2 / (G*M)) * a^3",
            "newton_grav": "F = G*m1*m2 / r^2",
            "vis_viva": "v^2 = G*M*(2/r - 1/a)",
            "angular_momentum": "L = m*r*v is conserved for central forces",
        },
        "constraints": [
            ("energy_conservation", "for any closed system S, d/dt E(S) = 0", "AXIOM"),
            ("momentum_conservation", "total momentum of an isolated system is constant", "AXIOM"),
        ],
        "derivations": [
            ("circular_velocity", ["newton_grav"],
             ["for a circular orbit gravity supplies the centripetal force",
              "G*M*m / r^2 = m*v^2 / r", "v^2 = G*M / r"], "v = sqrt(G*M / r)"),
            ("period_from_radius", ["kepler_third"],
             ["assume a near-circular orbit so a = r", "substitute a = r into Kepler's third law"],
             "T = 2*pi*sqrt(r^3 / (G*M))"),
        ],
        "claims": {
            "bound_orbit": "the orbit is gravitationally bound",
            "exact_eccentricity": "the exact eccentricity is determined",
            "parabolic_escape": "the body escapes on a parabola",
            "energy_negative": "the total orbital energy is negative",
        },
    },
    "propositional_logic": {
        "premises": {
            "modus_ponens": "from P and (P -> Q), infer Q",
            "given_p": "P holds",
            "implication_pq": "P -> Q holds",
            "given_not_r": "not R holds",
        },
        "constraints": [
            ("consistency", "no proposition is both asserted and denied", "AXIOM"),
            ("closure", "only conclusions derived under active premises are asserted", "DERIVED"),
        ],
        "derivations": [
            ("derive_q", ["modus_ponens", "given_p", "implication_pq"],
             ["P holds", "P -> Q is given", "apply modus ponens"], "Q holds"),
            ("derive_not_r", ["given_not_r"],
             ["not R is given as a premise", "no rule reintroduces R"], "not R holds"),
        ],
        "claims": {
            "q_true": "Q holds", "r_false": "R does not hold",
            "contradiction_absent": "the premise set is consistent",
            "p_and_q": "P and Q both hold",
        },
    },
    "euclidean_geometry": {
        "premises": {
            "triangle_sum": "the interior angles of a triangle sum to 180 degrees",
            "pythagorean": "in a right triangle, a^2 + b^2 = c^2",
            "parallel_postulate": "through a point off a line, exactly one parallel exists",
            "exterior_angle": "an exterior angle equals the sum of the remote interior angles",
        },
        "constraints": [
            ("planarity", "all figures lie in a single Euclidean plane", "AXIOM"),
            ("no_curvature", "the space has zero Gaussian curvature", "AXIOM"),
        ],
        "derivations": [
            ("angle_sum", ["triangle_sum"],
             ["label the interior angles a, b, c", "apply the triangle angle-sum rule"],
             "a + b + c = 180 degrees"),
            ("hypotenuse", ["pythagorean"],
             ["let the legs be a and b", "apply the Pythagorean relation"], "c = sqrt(a^2 + b^2)"),
        ],
        "claims": {
            "angles_sum_180": "the triangle's angles sum to 180 degrees",
            "right_triangle": "the triangle contains a right angle",
            "similar_triangles": "the two triangles are similar",
            "degenerate_case": "the triangle is degenerate",
        },
    },
    "probability": {
        "premises": {
            "bayes_rule": "P(A|B) = P(B|A)*P(A) / P(B)",
            "total_probability": "P(B) = sum_i P(B|A_i)*P(A_i)",
            "independence_def": "A and B are independent iff P(A and B) = P(A)*P(B)",
            "complement_rule": "P(not A) = 1 - P(A)",
        },
        "constraints": [
            ("kolmogorov", "probabilities are non-negative and the total measure is 1", "AXIOM"),
            ("normalization", "the distribution sums to 1 over the sample space", "AXIOM"),
        ],
        "derivations": [
            ("posterior", ["bayes_rule"],
             ["identify prior P(A) and likelihood P(B|A)", "apply Bayes' rule"],
             "P(A|B) is determined"),
            ("marginal", ["total_probability"],
             ["partition the space into A_i", "sum the conditional contributions"],
             "P(B) is determined"),
        ],
        "claims": {
            "events_independent": "the two events are independent",
            "posterior_computed": "the posterior is fully determined",
            "mutually_exclusive": "the events are mutually exclusive",
            "prior_known": "the prior distribution is known",
        },
    },
    "sequences_series": {
        "premises": {
            "arithmetic_sum": "sum of first n terms = n/2 * (2a + (n-1)d)",
            "geometric_sum": "sum of first n terms = a*(1 - r^n)/(1 - r)",
            "ratio_test": "a series converges if the limit of |a_{k+1}/a_k| < 1",
            "partial_sum": "S_n is the sum of the first n terms",
        },
        "constraints": [
            ("convergence_def", "a series converges iff its partial sums approach a limit", "DERIVED"),
            ("boundedness", "a convergent sequence is bounded", "AXIOM"),
        ],
        "derivations": [
            ("sum_n", ["arithmetic_sum"],
             ["identify first term a and common difference d", "apply the arithmetic-sum formula"],
             "S_n = n/2 * (2a + (n-1)d)"),
            ("geo_limit", ["geometric_sum"],
             ["assume magnitude of r below 1", "take the limit of the geometric sum"],
             "S = a / (1 - r)"),
        ],
        "claims": {
            "series_converges": "the series converges",
            "sum_finite": "the infinite sum is finite",
            "ratio_less_one": "the common ratio has magnitude below one",
            "diverges": "the series diverges",
        },
    },
}

STATUS_WEIGHTS = [("confirmed", 0.60), ("open", 0.25), ("denied", 0.15)]


def _weighted_status(rng):
    x = rng.random()
    c = 0.0
    for s, w in STATUS_WEIGHTS:
        c += w
        if x <= c:
            return s
    return "confirmed"


def _propagate(chain_id, domain, premises, base, n_hops):
    hops = []
    models = ["model_A", "model_B", "model_C", "model_D"][:n_hops + 1]
    for i in range(len(models) - 1):
        hops.append({
            "n": i + 1, "frm": models[i], "to": models[i + 1], "action": "load+verify",
            "constraints": copy.deepcopy(base["constraints"]),
            "derivations": copy.deepcopy(base["derivations"]),
            "claims": copy.deepcopy(base["claims"]),
            "verifications": copy.deepcopy(base["verifications"]),
            "trust": copy.deepcopy(base["trust"]),
        })
    return {"chain_id": chain_id, "domain": domain,
            "premises": copy.deepcopy(premises), "hops": hops}


def _build_one(domain, idx, rng):
    d = DOMAINS[domain]
    did, req, steps, concl = rng.choice(d["derivations"])
    prem_ids = list(req)
    extras = [p for p in d["premises"] if p not in prem_ids]
    rng.shuffle(extras)
    prem_ids += extras[:rng.randint(0, 1)]
    premises = [{"id": p, "text": d["premises"][p]} for p in prem_ids]

    cid, ctext, cbasis = rng.choice(d["constraints"])
    constraints = [{"id": cid, "text": ctext, "basis": cbasis}]

    dsteps = []
    for k, s in enumerate(steps, start=1):
        refs = [f"@FORMAL[{req[0]}]"] if (k == 2 and req) else []
        dsteps.append({"n": k, "text": s, "refs": refs})
    derivations = [{"id": did, "steps": dsteps, "conclusion": concl}]

    results = [{"step": k, "result": "holds"} for k in range(1, len(steps) + 1)]
    results.append({"step": "conclusion", "result": "holds"})
    verifications = [{"deriv": did, "results": results}]

    claim_ids = list(d["claims"])
    rng.shuffle(claim_ids)
    claims = [{"id": c, "text": d["claims"][c], "status": _weighted_status(rng)}
              for c in claim_ids[:3]]
    # guarantee at least one non-confirmed claim so status_inflation always has a valid target
    # (an "open" claim is still clean; this also matches the original hand-authored chains)
    if all(cl["status"] == "confirmed" for cl in claims):
        claims[rng.randrange(len(claims))]["status"] = "open"

    trust = [{"item": did, "label": "verified"}, {"item": prem_ids[0], "label": "trusted"}]
    if len(prem_ids) > 1 and rng.random() < 0.5:
        trust.append({"item": prem_ids[1], "label": "verified"})

    base = {"constraints": constraints, "derivations": derivations,
            "claims": claims, "verifications": verifications, "trust": trust}
    return _propagate(f"{domain}_{idx}", domain, premises, base, rng.randint(2, 3))


def generate_clean_chains(n=30, seed=0):
    rng = random.Random(seed)
    domains = list(DOMAINS)
    return [_build_one(domains[i % len(domains)], i, rng) for i in range(n)]


if __name__ == "__main__":
    from render import render_rl, render_json
    from check import check
    from collections import Counter
    chains = generate_clean_chains(30, seed=0)
    total_fp = 0
    for c in chains:
        dr = check(render_rl(c), "rl")
        dj = check(render_json(c), "json")
        total_fp += len(dr) + len(dj)
        if dr or dj:
            print(f"NOT CLEAN: {c['chain_id']}  rl={dr}  json={dj}")
    print(f"{len(chains)} generated; mechanical detections across all (MUST be 0): {total_fp}")
    stat = Counter()
    for c in chains:
        for cl in c["hops"][0]["claims"]:
            stat[cl["status"]] += 1
    print("claim-status mix:", dict(stat))
    print("hop counts:", dict(Counter(len(c["hops"]) for c in chains)))
    print("domains:", dict(Counter(c["domain"] for c in chains)))
