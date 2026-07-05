"""
audit.py — the LLM-auditor arm.

Interface: audit(trail_text, fmt) -> list of detections {error_class?, hop?, item?}.

The MOCK auditor (used to prove the pipeline in the sandbox) simulates an LLM auditor with
per-format detection/localization/false-positive rates. Its numbers are ILLUSTRATIVE, not
empirical. The real numbers come from live_audit() on the Tirana laptop.

live_audit(trail_text, fmt, call_model, ground_truth=None) uses a fixed, blind prompt and a
response parser. Wire call_model(prompt)->str to Together.ai or Anthropic on the laptop; the
rest of the pipeline is unchanged.
"""

import random
import re

# Fixed, blind auditor prompt (identical across formats). Blind = no mention of which format
# is "the product" and no injected-error hints.
AUDITOR_PROMPT = """You are auditing a multi-agent reasoning trace for reasoning failures that
occurred as the reasoning passed from one agent to the next.

Consider these failure classes:
  constraint_drift          - an active constraint's meaning changed across hops
  status_inflation          - a claim's certainty was raised (e.g. to "confirmed") without support
  trust_laundering          - content marked "trusted" at one hop was later reported "verified"
  dangling_reference        - a step cites a premise/constraint/derivation that is not defined
  verification_inconsistency- a verification reports a failure while a claim remains "confirmed"

List every failure you find, one per line, exactly as:
  CLASS | HOP_NUMBER | ITEM_ID | one-line reason
If you find no failures, write exactly: NONE

Trace:
---
{trace}
---
Findings:"""

_LINE_RE = re.compile(r"^\s*(?P<cls>[a-z_]+)\s*\|\s*(?:hop\s*)?(?P<hop>\d+)\s*\|\s*(?P<item>[^|]+?)\s*(?:\|.*)?$",
                      re.IGNORECASE)


def parse_auditor_response(text):
    """Parse an auditor's free-text findings into detections."""
    dets = []
    for line in text.splitlines():
        if line.strip().upper() == "NONE":
            continue
        m = _LINE_RE.match(line)
        if m:
            dets.append({"error_class": m.group("cls").strip().lower(),
                         "hop": int(m.group("hop")),
                         "item": m.group("item").strip()})
    return dets


def live_audit(trail_text, fmt, call_model, ground_truth=None):
    """Real auditor: call an LLM with the fixed prompt and parse its findings.
    `call_model` is a function prompt->response_text that you wire to your API on the laptop."""
    prompt = AUDITOR_PROMPT.format(trace=trail_text)
    response = call_model(prompt)
    return parse_auditor_response(response)


# ---------- mock auditor (sandbox only) --------------------------------------

# Illustrative per-format skill. RL ~ JSON (both structured); prose lower and noisier.
MOCK_SKILL = {
    "rl":    {"detect": 0.90, "localize": 0.95, "class": 0.90, "fp": 0.05},
    "json":  {"detect": 0.88, "localize": 0.92, "class": 0.88, "fp": 0.06},
    "prose": {"detect": 0.60, "localize": 0.70, "class": 0.65, "fp": 0.15},
}


def mock_audit(trail_text, fmt, ground_truth=None, rng=None):
    """Simulate an LLM auditor. Uses ground_truth to decide what it 'catches'. MOCK ONLY."""
    rng = rng or random.Random(0)
    sk = MOCK_SKILL[fmt]
    dets = []
    if ground_truth is None:
        # clean trail: occasionally emit a spurious detection (false positive)
        if rng.random() < sk["fp"]:
            dets.append({"error_class": "constraint_drift", "hop": 2, "item": "spurious"})
        return dets
    # injected trail
    if rng.random() < sk["detect"]:
        det = {"hop": ground_truth["hop"], "item": ground_truth["item"],
               "error_class": ground_truth["error_class"]}
        if rng.random() > sk["localize"]:
            det["hop"] = 1 if ground_truth["hop"] != 1 else 2  # detected presence, mislocalized
            det["item"] = "unknown"
        if rng.random() > sk["class"]:
            det["error_class"] = "unspecified"
        dets.append(det)
    if rng.random() < sk["fp"]:
        dets.append({"error_class": "constraint_drift", "hop": 1, "item": "spurious"})
    return dets


def audit(trail_text, fmt, ground_truth=None, rng=None):
    """Default entry point used by the sandbox pilot = mock auditor."""
    return mock_audit(trail_text, fmt, ground_truth, rng)


if __name__ == "__main__":
    print(parse_auditor_response("constraint_drift | hop 2 | energy | text changed\nNONE"))
    print(parse_auditor_response("status_inflation | 2 | exact_eccentricity | raised without support"))
