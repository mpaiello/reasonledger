"""
score.py — turn detections into the dependent-variable tables.

A trial = (chain, error_class_or_clean, format). For each trial we have detections from the
mechanical checker and from the LLM auditor. Against ground truth we compute, per
(format, auditor):
  - detection rate     : injected trials where the auditor flagged the correct presence (class match)
  - localization rate  : injected trials localized to the correct hop AND item
  - false-positive rate: clean trials on which any detection was raised

The decisive comparison is RL vs JSON (see PHASE1_demo_preregistration.md, Section 2).
"""

from collections import defaultdict


def _matches_presence(det, gt):
    return det.get("error_class") == gt["error_class"]


def _matches_localization(det, gt):
    return str(det.get("hop")) == str(gt["hop"]) and str(det.get("item")) == str(gt["item"])


def score_trial(detections, gt):
    """Return dict with detected/localized (for injected) or false_positive (for clean)."""
    if gt is None:
        return {"clean": True, "false_positive": len(detections) > 0}
    detected = any(_matches_presence(d, gt) for d in detections)
    localized = any(_matches_localization(d, gt) for d in detections)
    return {"clean": False, "detected": detected, "localized": localized}


class Tally:
    def __init__(self):
        self.inj = 0
        self.detected = 0
        self.localized = 0
        self.clean = 0
        self.fp = 0

    def add(self, s):
        if s["clean"]:
            self.clean += 1
            self.fp += 1 if s["false_positive"] else 0
        else:
            self.inj += 1
            self.detected += 1 if s["detected"] else 0
            self.localized += 1 if s["localized"] else 0

    def rates(self):
        det = self.detected / self.inj if self.inj else 0.0
        loc = self.localized / self.inj if self.inj else 0.0
        fp = self.fp / self.clean if self.clean else 0.0
        return det, loc, fp


def aggregate(records):
    """records: list of {format, auditor, score}. Return {(format,auditor): Tally}."""
    tallies = defaultdict(Tally)
    for r in records:
        tallies[(r["format"], r["auditor"])].add(r["score"])
    return tallies


def format_table(tallies):
    order_fmt = ["rl", "json", "prose"]
    order_aud = ["mechanical", "llm"]
    rows = []
    rows.append(f"{'format':7} {'auditor':11} {'detect':>7} {'localize':>9} {'false-pos':>10} {'n_inj':>6} {'n_clean':>8}")
    rows.append("-" * 62)
    for fmt in order_fmt:
        for aud in order_aud:
            t = tallies.get((fmt, aud))
            if not t:
                continue
            det, loc, fp = t.rates()
            rows.append(f"{fmt:7} {aud:11} {det:7.2f} {loc:9.2f} {fp:10.2f} {t.inj:6d} {t.clean:8d}")
    return "\n".join(rows)


def decision(tallies, d_thresh=0.20, l_thresh=0.15, mech_thresh=0.80):
    """Apply the locked decision rule (defaults from the pre-registration) to the LLM-auditor arm.
    Returns (verdict, explanation). NOTE: on mock data this is illustrative only."""
    rl = tallies.get(("rl", "llm"))
    js = tallies.get(("json", "llm"))
    rl_m = tallies.get(("rl", "mechanical"))
    js_m = tallies.get(("json", "mechanical"))
    if not (rl and js):
        return "N/A", "insufficient data"
    rl_det, rl_loc, _ = rl.rates()
    js_det, js_loc, _ = js.rates()
    d_gap, l_gap = rl_det - js_det, rl_loc - js_loc

    mech_edge = False
    if rl_m and js_m:
        rlm_det, _, _ = rl_m.rates()
        jsm_det, _, _ = js_m.rates()
        mech_edge = (rlm_det - jsm_det) >= mech_thresh  # RL catches a class JSON can't, mechanically

    if (d_gap >= d_thresh and l_gap >= l_thresh) or mech_edge:
        return "STRONG GO", (f"RL beats info-matched JSON on the LLM auditor "
                             f"(detect +{d_gap:.2f}, localize +{l_gap:.2f})"
                             + (" and/or holds a mechanical-detection edge." if mech_edge else "."))
    if abs(d_gap) < d_thresh and abs(l_gap) < l_thresh:
        return "WEAK GO / standard play", ("RL ties info-matched JSON on detection "
                                           f"(gap {d_gap:+.2f}). Value is standardization and off-the-shelf "
                                           "checkability, not a detection edge. Pursue as an open standard "
                                           "and reference checker; do not build a detection-moat venture.")
    return "NO-GO", (f"RL does not beat info-matched JSON (detect gap {d_gap:+.2f}). "
                     "Keep the published standard; stop the venture spend.")
