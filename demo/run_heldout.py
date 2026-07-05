#!/usr/bin/env python3
"""
run_heldout.py -- pre-committed held-out evaluation of FROZEN auditor prompts.

STATUS: v1.0 -- FROZEN at the pre-commit's commit. Decoding parameters confirmed against
run_live.py (temperature = run_live.TEMPERATURE = 0.0; max_tokens = 800 in call_model);
the runner reuses run_live.call_model unchanged so operating conditions are identical to
the original runs. The live path refuses to run without --precommit-sha.

Implements PRECOMMIT_heldout_v8.3_20260705.md:
  - Fresh clean chains   (default n=60, seed 260705)
  - Fresh injected set   (default 3 source chains at seed 260706, each injected once per
                          class across the five classes = 15 trials)
  - Cells: descriptive, minimal, minimal_plus_caution (mechanical splice, see below),
           strict, precision -- all imported FROZEN from prompts.py; nothing retyped
  - Mechanical checker scored on both fresh sets (local, no API cost)
  - RL format only; strong model only; temperature and decoding params are whatever
    run_live.call_model applies (its sha256 is embedded; finalize after review)
  - Output: results_heldout_<UTCSTAMP>.json -- never overwrites anything
  - Transport failures: retried, then recorded transport_failed and EXCLUDED from
    denominators; exclusion count reported
  - Diversity check: fresh clean traces vs regenerated seed-0 originals
    (exact-hash collisions must be zero; max line-Jaccard per fresh trace disclosed)

Expected live volume at defaults: 5 cells x 75 trials = 375 auditor calls, one model.

Mechanical construction of the minimal_plus_caution cell (pre-committed rule):
  CAUTION is extracted verbatim from the frozen PRECISION text as the contiguous span
  from "Precision matters far more than recall" through "Many traces are clean."
  (inclusive), by substring index with assertion. The cell is then
  minimal-without-tail + "\n" + CAUTION + tail. No newly authored auditor-visible text.
"""

import argparse
import datetime
import hashlib
import json
import os
import random
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate import generate_clean_chains
from inject import INJECTORS, ERROR_CLASSES
from render import RENDERERS
from check import check
from score import score_trial, Tally
from prompts import PROMPTS, MINIMAL, PRECISION, _TAIL
from audit import parse_auditor_response, mock_audit
import run_live

VERSION = "1.0"
FMT = "rl"

GOVERNING_FILES = ["prompts.py", "audit.py", "generate.py", "inject.py", "render.py",
                   "check.py", "score.py", "run_live.py", "canonical.py",
                   os.path.basename(__file__)]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def sha_text(s):
    return sha(s.encode("utf-8"))


def file_hashes():
    here = os.path.dirname(os.path.abspath(__file__))
    out = {}
    for name in GOVERNING_FILES:
        p = os.path.join(here, name)
        out[name] = sha(open(p, "rb").read()) if os.path.exists(p) else "MISSING"
    return out


def build_caution_cell():
    start = "Precision matters far more than recall"
    end = "Many traces are clean."
    i = PRECISION.index(start)
    j = PRECISION.index(end) + len(end)
    caution = PRECISION[i:j]
    assert caution in PRECISION
    assert MINIMAL.endswith(_TAIL), "minimal prompt does not end with the shared tail"
    core = MINIMAL[: -len(_TAIL)]
    return core + "\n" + caution + _TAIL, caution


def build_sets(n_clean, n_src, seed_clean, seed_inj):
    clean = [(c, None) for c in generate_clean_chains(n_clean, seed=seed_clean)]
    injected = []
    for c in generate_clean_chains(n_src, seed=seed_inj):
        for cls in ERROR_CLASSES:
            injected.append(INJECTORS[cls](c))
    return clean, injected


def diversity_check(fresh_clean):
    originals = generate_clean_chains(30, seed=0)
    orig_rl = [RENDERERS[FMT](c) for c in originals]
    orig_hashes = {sha_text(t) for t in orig_rl}
    orig_lines = [set(l.strip() for l in t.splitlines() if l.strip()) for t in orig_rl]
    rows = []
    for c, _ in fresh_clean:
        t = RENDERERS[FMT](c)
        lines = set(l.strip() for l in t.splitlines() if l.strip())
        jmax = max(len(lines & o) / len(lines | o) for o in orig_lines)
        rows.append({"chain_id": c.get("chain_id"), "trace_sha256": sha_text(t),
                     "identical_to_original": sha_text(t) in orig_hashes,
                     "max_line_jaccard_vs_originals": round(jmax, 4)})
    js = sorted(r["max_line_jaccard_vs_originals"] for r in rows)
    summary = {"n_fresh": len(rows),
               "n_identical_to_originals": sum(r["identical_to_original"] for r in rows),
               "jaccard_min": js[0], "jaccard_median": js[len(js) // 2], "jaccard_max": js[-1]}
    return summary, rows


def call_with_retries(prompt, model, max_attempts, wait):
    errors = []
    for attempt in range(1, max_attempts + 1):
        try:
            return run_live.call_model(prompt, model), errors
        except Exception as e:
            errors.append("attempt %d: %s" % (attempt, str(e).splitlines()[0][:120]))
            if attempt < max_attempts:
                time.sleep(wait)
    return None, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--n-clean", type=int, default=60)
    ap.add_argument("--n-inject-src", type=int, default=3)
    ap.add_argument("--seed-clean", type=int, default=260705)
    ap.add_argument("--seed-injected", type=int, default=260706)
    ap.add_argument("--precommit-sha", default=None,
                    help="sha256 of the committed pre-commit file; required for live runs")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--wait", type=int, default=5)
    args = ap.parse_args()

    if not args.mock and not args.precommit_sha:
        sys.exit("live run refused: --precommit-sha required (commit the pre-commit file first)")

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model = run_live.MODELS["strong"]

    caution_cell, caution = build_caution_cell()
    cells = {"descriptive": PROMPTS["descriptive"],
             "minimal": PROMPTS["minimal"],
             "minimal_plus_caution": caution_cell,
             "strict": PROMPTS["strict"],
             "precision": PROMPTS["precision"]}

    clean, injected = build_sets(args.n_clean, args.n_inject_src,
                                 args.seed_clean, args.seed_injected)
    div_summary, div_rows = diversity_check(clean)

    trials_meta = []
    for set_name, trials in (("clean", clean), ("injected", injected)):
        for idx, (chain, gt) in enumerate(trials):
            t = RENDERERS[FMT](chain)
            trials_meta.append({"set": set_name, "idx": idx,
                                "chain_id": chain.get("chain_id"),
                                "gt_class": gt["error_class"] if gt else "clean",
                                "trace_sha256": sha_text(t), "trace_text": t})

    n_calls = len(cells) * (len(clean) + len(injected))
    print("held-out run %s: %d clean + %d injected; cells=%s; ~%d auditor calls (%s)"
          % (stamp, len(clean), len(injected), list(cells), n_calls,
             "MOCK" if args.mock else "LIVE"))
    print("diversity: %s" % div_summary)

    # mechanical arm, both sets, no API
    mech = defaultdict(Tally)
    for set_name, trials in (("clean", clean), ("injected", injected)):
        for chain, gt in trials:
            t = RENDERERS[FMT](chain)
            s = score_trial(check(t, FMT), gt)
            mech["all"].add(s)
            mech[gt["error_class"] if gt else "clean"].add(s)

    records = []
    tallies = defaultdict(Tally)
    excluded = defaultdict(int)
    for pname, tmpl in cells.items():
        for set_name, trials in (("clean", clean), ("injected", injected)):
            for idx, (chain, gt) in enumerate(trials):
                t = RENDERERS[FMT](chain)
                rec = {"cell": pname, "set": set_name, "idx": idx,
                       "chain_id": chain.get("chain_id"),
                       "gt_class": gt["error_class"] if gt else "clean"}
                if args.mock:
                    rng = random.Random(abs(hash((chain.get("chain_id"), FMT, idx, pname))) % (2 ** 32))
                    dets, errors, resp = mock_audit(t, FMT, gt, rng), [], "(mock)"
                else:
                    resp, errors = call_with_retries(tmpl.format(trace=t), model,
                                                     args.max_attempts, args.wait)
                    dets = parse_auditor_response(resp) if resp is not None else None
                if dets is None:
                    rec.update({"status": "transport_failed", "errors": errors})
                    excluded[pname] += 1
                else:
                    rec.update({"status": "ok", "retries": errors,
                                "raw_response": resp, "detections": dets})
                    s = score_trial(dets, gt)
                    tallies[(pname, "all")].add(s)
                    tallies[(pname, rec["gt_class"])].add(s)
                records.append(rec)
        print("  cell %-22s done (%d excluded)" % (pname, excluded[pname]))

    def block(t):
        det, loc, fp = t.rates()
        return {"detect": round(det, 3), "localize": round(loc, 3),
                "false_positive": round(fp, 3), "n_injected": t.inj, "n_clean": t.clean}

    results = {}
    print("\n%-22s %7s %10s %6s %8s %9s" % ("cell", "detect", "false-pos", "n_inj", "n_clean", "excluded"))
    print("-" * 68)
    for pname in cells:
        t = tallies[(pname, "all")]
        det, _, fp = t.rates()
        print("%-22s %7.2f %10.2f %6d %8d %9d" % (pname, det, fp, t.inj, t.clean, excluded[pname]))
        results[pname] = {"overall": block(t), "excluded_transport_failed": excluded[pname],
                          "per_class": {k[1]: block(v) for k, v in tallies.items()
                                        if k[0] == pname and k[1] != "all"}}
    results["mechanical"] = {"overall": block(mech["all"]),
                             "per_class": {k: block(v) for k, v in mech.items() if k != "all"}}

    out = {"config": {"runner_version": VERSION, "utc_stamp": stamp,
                      "precommit_sha256": args.precommit_sha, "mock": args.mock,
                      "model": model, "format": FMT,
                      "decoding_params": {"temperature": run_live.TEMPERATURE, "max_tokens": 800,
                                          "source": "run_live.call_model, sha256 in governing_file_sha256"},
                      "n_clean": len(clean), "n_injected": len(injected),
                      "seed_clean": args.seed_clean, "seed_injected": args.seed_injected,
                      "cells": {k: {"sha256": sha_text(v)} for k, v in cells.items()},
                      "caution_span_sha256": sha_text(caution),
                      "governing_file_sha256": file_hashes()},
           "diversity": {"summary": div_summary, "per_trace": div_rows},
           "results": results,
           "trials_meta": trials_meta,
           "records": records}

    fname = "results_heldout_%s.json" % stamp
    if os.path.exists(fname):
        sys.exit("refusing to overwrite " + fname)
    with open(fname, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote %s" % fname)
    if args.mock:
        print("MOCK proves wiring only; the mock auditor ignores the prompt by design.")


if __name__ == "__main__":
    main()
