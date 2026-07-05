# Reasonledger Phase 1 — Reasoning-Ledger Demo
## Pre-Registered Design & Decision Rule

**Date:** 2026-06-30. **Owner:** M. Aiello. **Status:** design locked before build; decision rule locked before data.
**Purpose of this document:** define the decisive test of whether Reasonledger's audit layer has real value, with the go/no-go criteria fixed in advance so the result cannot be read selectively. This follows the project's pre-registration discipline and the roadmap's rule that the test precedes the spend.

---

## 1. The claim under test

Reasonledger's structured, enforced, mechanically-checkable audit layer — provenance across hops, three-way epistemic status, verified-versus-trusted labels, per-step verification, derivation trace — lets an auditor **detect and localize reasoning failures in a multi-agent chain better than raw tracing does**.

**Explicitly not under test** (excluded by prior analysis): frontier single-hop correctness (saturated), token efficiency (commoditized), any claim about model cognition (cut). The demo measures auditability, nothing else.

## 2. The decisive contrast (read this first)

The test compares three renderings of the **same reasoning content**:

- **RL** — Reasonledger notation.
- **JSON-matched** — JSON carrying the *same fields* (provenance, status, verification, trust). The critical baseline.
- **Prose-matched** — natural-language narration carrying the same information.

(Optional floor: **Prose-raw** — what an agent emits when simply asked to explain, with no structured fields. The "what people do now" baseline.)

**Beating Prose is not evidence for a venture.** Structured self-reporting beats prose trivially, and any format can carry structured self-reports. The claim stands or falls on **RL versus JSON-matched**: does the notation and its defined semantics add value beyond the fields themselves? That is the contrast the decision rule turns on.

## 3. Hypotheses

- **H1 (detection).** On injected reasoning failures, RL yields a higher error-detection rate than JSON-matched.
- **H2 (localization).** When a failure is detected, RL yields more accurate localization (correct hop/step) than JSON-matched.
- **H3 (mechanical checkability).** A mechanical checker over RL catches classes of failure automatically (constraint violation, status inflation, trust laundering) that the JSON-matched and prose conditions require a human/LLM read to catch, or catches them with materially less bespoke tooling.
- **Null (the honest default).** RL ≈ JSON-matched on H1–H2, and H3 reduces to "JSON can do this too if you build the equivalent schema and rules." If the null holds, Reasonledger's value is standardization, not detection — see the decision rule.

## 4. Design

A multi-hop reasoning pipeline. A canonical clean chain is generated once with full semantic content — claims with status, derivation steps with a conclusion, active constraints, per-hop provenance, verification results, trust labels — then **rendered** into RL, JSON-matched, and Prose-matched by templates. Rendering once and varying only format isolates the audit question from the (saturated, confounded) question of whether format changes what agents generate.

- **Domain:** neutral technical content (orbital mechanics, logic, quantitative inference). No observer content; firewall holds.
- **Chain length:** 3–4 hops.
- **Primary test = audit** (controlled injection into rendered trails). This directly tests the venture's core claim and is cleanly falsifiable.
- **Secondary/exploratory = live generation** (optional): do agents communicating live in RL vs JSON produce different natural error rates or more detectable structure? Lighter, confounded by saturation, run only if the primary test is promising.

## 5. Error-injection protocol (ground truth)

Errors are injected **programmatically into copies of the clean rendered trails**, identically across the three formats, so ground truth is exact and corruption is matched. Five failure classes, each targeting a Reasonledger-designed detection point, plus clean controls:

1. **Constraint violation** — a later step contradicts an earlier `@LOGIC` constraint.
2. **Status inflation** — a claim marked `open` upstream is reported `confirmed` downstream with no new justification.
3. **Trust laundering** — content received "on trust" at hop *n* is reported as "verified" at hop *n+k*.
4. **Semantic drift** — a constraint's meaning erodes via paraphrase across hops (the drift the original ANN runs observed on `@LOGIC[symmetry]`).
5. **Fabricated step** — a derivation step that does not follow from its predecessors.
6. **Clean** — no injected error (measures false-positive rate).

Each class × several instances × 3 formats. Injection method is specified per class; classes that inject cleanly into structured formats but only approximately into prose are flagged, and that asymmetry is itself reported (it is part of the finding).

## 6. Auditors

Two, applied to every trail:

- **Mechanical checker.** Extends `validator.py` with consistency rules: constraint-preservation across hops, status monotonicity (no unjustified `open`→`confirmed`), trust-provenance (no verified-without-a-verification-record), derivation closure. For JSON-matched, an equivalent schema + rule set is written; the **effort to build and the coverage achieved are recorded and compared** (this is where H3 lives — RL ships the semantics and checker; JSON requires rolling your own).
- **LLM auditor.** A fresh model instance given one trail and a fixed prompt: "find and localize any reasoning failures." Identical prompt across all conditions. Blind to which format is "the product." Its detections are parsed and scored against ground truth.

## 7. Dependent variables

1. **Detection rate** — fraction of injected errors caught, per condition.
2. **Localization accuracy** — fraction of caught errors correctly localized to hop/step.
3. **False-positive rate** — flags raised on clean trails.
4. **Mechanical-checkability** — fraction of each error class caught *automatically* per condition, plus the bespoke-tooling effort required to reach it.
5. **(Secondary) Audit effort** — auditor tokens/time per trail.

## 8. Models, sample, cost

- **Models:** a cross-architecture mix including at least one strong and one weak/cheap model, to test whether any RL advantage is larger on weaker models (a stated hypothesis). Architecturally distinct.
- **Sample (pilot):** 6 classes × ~4 instances = ~24 chains × 3 formats = ~72 trails, each seen by the mechanical checker and the LLM auditor. Enough to see a material, consistent effect; not a publication-grade N.
- **Cost:** low — on the order of a few hundred API calls, well under a few dollars. If GO, scale N up for the paper.
- **Constraint:** live auditor runs use the Together.ai SDK and the Anthropic key on the **Tirana laptop**; the sandbox blocks the required APIs. Keys go in the terminal as session-scoped env vars after `Set-PSReadLineOption -HistorySaveStyle SaveNothing`, never in chat. No angle-bracket placeholders in commands.

## 9. Analysis plan

Descriptive comparison of the DVs across conditions, with simple effect sizes; the pilot N supports a material-and-consistent-difference judgment rather than significance testing. The one contrast that decides the outcome is **RL versus JSON-matched** on H1–H3, reported per error class and per model tier. Prose conditions are context, not the test.

## 10. Decision rule (LOCKED — set before any data)

Three outcomes, and the modest ones are real:

- **STRONG GO → build Phase 3.** On injected errors, RL detection ≥ JSON-matched + 20 percentage points AND localization ≥ JSON-matched + 15 points, holding on ≥2 model tiers, with RL false-positive rate no worse than JSON-matched by more than 10 points. OR the mechanical checker catches a failure class (constraint violation, status inflation, or trust laundering) at ≥80% on RL where JSON-matched/prose require a human read. This is a genuine detection or automation edge; a venture has something to defend.

- **WEAK GO → open standard + light tooling, no detection-moat venture.** RL ≈ JSON-matched on detection and localization (within noise), BUT RL's off-the-shelf checker matches bespoke-JSON checking with materially less setup, and cross-agent consistency is higher. The value is standardization — a shared, checkable semantics so teams do not reinvent provenance/status schemas. Pursue adoption and a reference checker; do **not** build a venture premised on catching what others cannot, because the data say that edge is not there.

- **NO-GO → stop the venture; keep the published contribution.** RL ≤ JSON-matched on every DV and beats only prose. The value was "ask the model to self-report," which is a prompting choice. Reasonledger remains a clean, cited, defensively-published standard, which is an honorable resting state. Do not spend further on apparatus.

**Pre-commitment:** these thresholds are the numbers, fixed now. A mixed result is read against this rule, not around it. (Thresholds are defaults; finalize the exact numbers before the first run, then they are locked.)

## 11. Artifacts produced

Whatever the outcome, the demo yields: the harness (renderers, injector, mechanical checker, scorer); the 72 trails; the DV tables (detection/localization/FP × class × model tier); and a simple **ledger-view visualization** that renders an RL trail as an inspectable audit timeline highlighting where status changed, where a constraint was violated, and where trust was laundered. Under STRONG or WEAK GO that visualization is the venture's proof-of-concept and the paper's figure; under NO-GO it is still a clean illustration for the published standard.

## 12. Honest risks

- **The likely outcome is WEAK GO, not STRONG.** The saturation results suggest a capable auditor finds most injected errors under any format that carries the information. If so, RL's advantage is standardization and off-the-shelf checkability, not superior detection — a real but modest value, and a very different business than "we catch what others miss."
- **Mechanical-checkability may be the only place RL wins.** That is acceptable and is why H3 is first-class: an automatic linter/CI for agent reasoning is a genuine feature. But JSON-plus-schema can approach it, so the honest claim is convenience and standardization, not exclusivity.
- **NO-GO is a live possibility.** The design permits it, and taking it would be the correct call, not a failure.

## 13. Build plan

Most of the harness is pure code and can be built and tested in the sandbox with a mock auditor before any live run: the three renderers, the injector with ground-truth labels, the mechanical checker (extending `validator.py`), the scorer, and the visualization. Only the LLM-auditor arm needs live APIs and runs on the Tirana laptop.

Sequence:
1. Canonical clean-chain content (hand-author 3–4 seeds to start cheap; generate more if promising).
2. Three renderers (content → RL / JSON-matched / Prose-matched).
3. Injector (5 classes + clean, with ground-truth labels), applied equivalently across formats.
4. Mechanical checker (RL rules + JSON-matched equivalent; record coverage and setup effort).
5. Scorer (detections → DV tables) with a mock auditor, to prove the pipeline end-to-end in the sandbox.
6. Ledger-view visualization.
7. Hand off to the laptop for the live LLM-auditor arm; collect trails; score; compare against the Section 10 rule.

Items 1–6 I can build and test here. Item 7 runs on the laptop.

---

*Design and decision rule locked 2026-06-30. The decisive contrast is Reasonledger versus information-matched JSON; beating prose is not evidence. The rule admits STRONG GO, WEAK GO, and NO-GO, and NO-GO is a legitimate result.*
