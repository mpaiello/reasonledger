# Phase 1 Demo Harness

The buildable half of the reasoning-ledger test (items 1–6 of the pre-registration).
Everything here runs offline with a **mock auditor**, so the whole pipeline is proven before
the live arm ever runs. Only the live LLM-auditor arm (item 7) needs API keys, and it runs on
the Tirana laptop by swapping one function call.

See `../PHASE1_demo_preregistration.md` for the design, hypotheses, and the **locked decision rule**.
The decisive comparison is **RL vs information-matched JSON**; beating prose proves nothing.

## Module map

| File | Role |
|---|---|
| `canonical.py` | format-agnostic chain model + clean seed chains (source of truth) |
| `render.py` | renders one chain into RL, information-matched JSON, and information-matched prose |
| `inject.py` | five error injectors + clean control, each with exact ground truth |
| `check.py` | mechanical checker: parses RL/JSON and applies five cross-hop consistency rules (prose is not checkable, by design) |
| `audit.py` | auditor interface: fixed blind prompt + parser, a **mock** auditor, and a `live_audit()` stub |
| `score.py` | detection / localization / false-positive rates + the decision rule |
| `visualize.py` | renders a trail as an HTML "ledger view" with anomalies highlighted |
| `run_pilot.py` | runs the whole matrix end-to-end with the mock auditor |

## Run the mock pilot (offline)

```
cd demo
python3 run_pilot.py            # or: python3 run_pilot.py 20   (replicates)
```

Produces the DV table, `results.json`, and `ledger_view.html`. The mock rates are
illustrative, not empirical — they exist to prove the pipeline and to show the pattern the
design predicts: RL and JSON are equally mechanically checkable (both structured), and on the
mock LLM arm RL ≈ JSON. The real numbers replace the mock in the step below.

## Wire the live auditor (Tirana laptop, item 7)

Only one function changes. In `run_pilot.py`, replace the mock call

```python
llm = audit(trail, fmt, gt, rng)
```

with the live auditor, passing a `call_model` you wire to your API:

```python
from audit import live_audit

def call_model(prompt: str) -> str:
    # Together.ai or Anthropic. Key from a session env var, never in code:
    #   $env:TOGETHER_API_KEY (after Set-PSReadLineOption -HistorySaveStyle SaveNothing)
    ...  # send prompt, return the model's text
    return response_text

llm = live_audit(trail, fmt, call_model)      # ground truth is NOT shown to the auditor
```

The auditor prompt is fixed and blind (identical across formats, no error hints); its findings
are parsed by `parse_auditor_response`. Run at least one strong and one weak/cheap model, and
score against the same `results.json` shape. Then read the RL-vs-JSON gap against the locked
thresholds in the pre-registration.

## Honest reminder

The mechanical arm already shows the likely story: structured JSON is as mechanically
auditable as Reasonledger, so Reasonledger's edge is standardization and off-the-shelf
checkability, not catching what JSON can't. The live LLM arm is what decides STRONG GO vs
WEAK GO vs NO-GO. Read it against the rule, not around it.
