# PRECOMMIT — Held-Out Evaluation of Frozen Auditor Prompts (Paper 4, v8.3 gate)

**Status:** COMPLETE — ready to commit. All register values verified on the Tirana laptop 2026-07-05. Binding from the commit timestamp. No edits after commit. A correction requires a new dated file that supersedes this one before any trace generation; otherwise the run is void.
**Date drafted:** 2026-07-05. **Commit date:** TBD at commit.
**Lineage:** implements Option B of HANDOFF_Paper4_v8.3.md §3, amended per session 2026-07-05: a fresh injected arm is added so the run measures the full operating point, not false positives alone. Answers the converged remedy in PANEL_READOUT_v8.2.md §1. This file's sha256 and repo commit hash are recorded in the run log and cited in the v8.3 reproducibility appendix as the pre-registration text.

---

## 1. Question under test

Whether the frozen strict prompt reproduces its observed operating point (false-positive rate approximately 0.00, detection approximately 0.93) on traces it has never been exposed to, drawn from the same generator. This tests generalization beyond the thirty clean traces the prompt was written against. It does not and cannot test generalization beyond this generator's distribution, beyond this trace format, or beyond this model; those remain future work under every outcome.

No causal claim about which prompt property drives the rate is licensed by this design under any outcome. The run contains no paraphrase control. All results are reported in observation language.

## 2. Design

Four prompt cells, two fresh trace sets, one auditor model, one scoring pass per cell per set. Every string an auditor sees is frozen before generation.

Cells:

- (a) **descriptive** (frozen text, hash in §5). Positive control: establishes whether the fresh clean set elicits the failure mode at all.
- (b) **minimal** (frozen text, hash in §5). Baseline for cell (c).
- (c) **minimal-plus-caution**: constructed mechanically at run time. The caution text is extracted verbatim from the frozen precision prompt as the contiguous span from "Precision matters far more than recall" through "Many traces are clean." inclusive, by substring index with an assertion check, and spliced after the minimal prompt's instruction block, before the shared trace tail, joined by single newlines. No newly authored auditor-visible text. The panel's named missing cell. Exploratory.
- (d) **strict** (frozen text, hash in §5). The cell under test.
- (e) **precision** (frozen text, hash in §5). Replication of the original caution control on held-out data; completes the fresh-data curve.

In addition, the mechanical checker is scored on both fresh sets (local, no API cost). This addresses, within the generator's distribution, the read-out's cluster C boundary that the checker's false-positive behavior on independently varied valid traces was untested. Its results are reported as exact counts under the verification-by-construction framing; no headline-metric framing is reintroduced.

Fresh trace sets, produced by the existing generator and injector, unmodified:

- Clean: N = 60, generation seed 260705.
- Injected: 3 source chains at generation seed 260706, each injected once per class across the five classes, 15 trials. This mirrors the original run's mechanism (3 source chains at seed 4242, per `run_prompts.py`).

Contingency: if the generator cannot produce novel chains at a new seed (fixed corpus, no stochastic path), STOP before any scoring; the design is amended by a new superseding pre-commit.

Auditor: the original run's capable model (Llama-3.3-70B), served via Together. Probe before spend and record the exact served id. Temperature 0.0 and max_tokens 800, identical to the original runs (run_live.TEMPERATURE and the literal in run_live.call_model); the held-out run reuses call_model unchanged so the operating conditions are frozen, including any truncation behavior the original numbers were produced under. If the original endpoint id is no longer served, the closest same-weights endpoint substitutes and the substitution is logged as a deviation; weights identity governs, serving id may drift.

Metrics: the operational definitions of false positive and detection are those of the original evaluation, bound by the scorer hash in §5 and verified by source read 2026-07-05: detection is any flag whose error class matches ground truth (presence by class match); localization is any flag matching ground-truth hop and item (independent of class); false positive is trial-level, any flag at all on a clean trace. False-positive rate is measured on the clean set, detection on the injected set, with per-class counts. Exact counts (x/60, x/15) are reported alongside rates in all cases. Injection targets the final hop by default (inject.py), so failure position is homogeneous; disclosed in the v8.3 limitations.

## 3. Interpretation rules (fixed before data)

- **R1. Positive-control gate.** If descriptive false positives on the fresh clean set fall below 0.80 (48/60), the fresh set is declared non-comparable: it does not elicit the failure mode, no generalization conclusion is drawn in either direction, and the result is reported as exactly that.
- **R2. Replication supported.** Strict false positives at or below 0.05 (3/60) AND strict detection at or above 0.80 (12/15). v8.3 then states the scoped claim: the post-hoc strict prompt reproduces its operating point on unseen traces from the same generator. Cross-distribution and cross-format generalization remain untested and are stated as such.
- **R3. Overfit signal.** Strict false positives at or above 0.20 (12/60). v8.3 reports the overfit interpretation as confirmed for the strict prompt.
- **R4. Attenuation.** Any outcome between R2 and R3, including low false positives with detection below 0.80, is reported descriptively with no generalization claim.
- **R5.** Cell (c) is exploratory under all outcomes and is reported in observation language only.
- **R6.** Whatever comes is reported. No outcome makes this run unreported or rerun.
- **R7.** Mechanical-checker results on the fresh sets are reported as exact counts under the verification-by-construction framing; no threshold applies and no headline-metric framing is reintroduced under any outcome.

Threshold values may be adjusted before commit, never after.

## 4. One-shot and hygiene clauses

- No prompt text is edited between this commit and v8.3 submission. If R3 obtains, the paper reports it; further prompt engineering is future work.
- One generation per set at the stated seeds. One scoring run per cell per set. Transport failures (API error, timeout, unparseable output) may be retried; each retry is logged. A trial that fails after the retry limit is recorded as transport_failed and EXCLUDED from denominators, with the exclusion count reported; it is never silently scored as an empty detection list, which would bias both rates downward. A completed, parseable scoring call is never re-sampled.
- Result files carry UTC timestamps, model id, effective parameters, and the sha256 of this file, of each prompt text as sent, and of each trace file.
- Near-duplicate check (descriptive, does not gate scoring): sha256 of each fresh trace is compared against the thirty original clean traces; zero identical files is required. Maximum line-level Jaccard similarity of each fresh trace against the original set is computed and the distribution is disclosed in the v8.3 appendix. The check script is new code; it touches no prompt and no scoring path.
- Deviations are logged verbatim in HELDOUT_RUN_LOG.md at the moment they occur.

## 5. Frozen artifact register (fill from laptop, then commit)

Canonical prompt text is the string recorded in the original evaluation's archived result or config files, that is, what was actually sent, not what a label in `demo/prompts.py` currently points at. Verification is by text, never by name: the prompt set was renamed mid-session and the label `default` pointed at a different prompt in one intermediate run.

**Resolved 2026-07-05.** The fallback chain above proved unnecessary: `audit.py` (untouched since 12:22:30 on 2026-07-01, before all three runs) defines AUDITOR_PROMPT, verified byte-identical to `prompts.py`'s descriptive text by import-diff (`audit_vs_descriptive: IDENTICAL`). `prompts.py` (15:33:25) predates the run-2 results (15:38:48) and is untouched since. Current `prompts.py` is therefore the canonical text for all four original prompts, and one prompt (sha256 8196…7b0f) threads the pre-registered run, the diagnostic, and the prompt-curve top row.

| item | canonical source | sha256 |
|---|---|---|
| descriptive prompt text (= audit.py AUDITOR_PROMPT, verified identical) | demo/prompts.py, verified 2026-07-05 | 8196461731de50102f79a8663d29e1104417a5ec815e8bbdf35b2c5314867b0f |
| minimal prompt text | demo/prompts.py, verified 2026-07-05 | 8ff5fb34dfd8e8426dc8b452b12dc4abd938d01b959002f085b87dd3c7a60f08 |
| strict prompt text | demo/prompts.py, verified 2026-07-05 | a26164638635651085fd2d3ccb51428023dcc420d2e356e98b06f69c3852ddaa |
| precision prompt text | demo/prompts.py, verified 2026-07-05 | f2d875f7baf226423d1a311dba78cf215d3bdbd74c85c4bee61e4a6f42eceeba |
| caution span, verbatim, extracted from the frozen precision prompt (267 chars) | derived per §2 rule; confirmed on laptop 2026-07-05 | d9280164257a30c920a6d0d5817b94a43e470afa23e12035cb9a43a8dc924bae |
| constructed cell (c), minimal_plus_caution (589 chars) | derived per §2 rule; confirmed on laptop 2026-07-05; echoed in the runner's config output | e377692104b1434a3eef516acb933246033be37ae2b07c23d10c5f5efe36a91c |
| prompts file | demo/prompts.py | 511e2c657704131263979ca9adef27e8be08377bfddff4183cb631858e9fc0e1 |
| auditor module (AUDITOR_PROMPT, parser) | demo/audit.py | 0e2a312c566aa616b2588f9e8166bd9294b639af5d1290c74bcaa3e76088cd16 |
| generator script | demo/generate.py | e906a74b3bbfa90541a30c3ac7f86eba955e9f985913e5a7829a0c319f0f9f2d |
| injector script | demo/inject.py | 216b6a9eac278ff12934a3efad9c69ce32a960520ad27f289b2236af05e98805 |
| scorer and metric definitions | demo/score.py | 81522764b6e24089c846209dd8ca6582ffb18d1af38b4d45b2121a4f39a1bb46 |
| mechanical checker | demo/check.py | b186e58bbf4ccded0c4977dc5ed43acc747bde01fea2008ca4188051e4a97f81 |
| canonical chains (imported by run_live) | demo/canonical.py | 6dde1ddf4370eff42e37cecc0a6e8c1e698a129aa57a8c2e94a837ef07372450 |
| prompt-run harness (provenance of the original run) | demo/run_prompts.py | bc83ca6853cfce32b7f21da47b073593601800f0c079ad93e73963d427df131e |
| renderer (what the auditor sees) | demo/render.py | d0b1fc8274ce9157bc1940b02aefb460190088d9ee09664bf54a0b04dddd9f2a |
| held-out runner v1.0, frozen at this file's commit | demo/run_heldout.py | 55d75a0aab8eb90ec9de2364abc3712806209664715c4cef01c283f715ba576d |
| original run config: model meta-llama/Llama-3.3-70B-Instruct-Turbo; temperature 0.0 (run_live.TEMPERATURE); max_tokens 800 (literal in run_live.call_model) | demo/run_live.py | 5fc5b47b76d796b9eabf419ef685dc3275bf6db1a93a3a3d472a3c92dd5e4812 |
| pre-registration text | PHASE1_demo_preregistration.md, repo root | 5faa3774a617b42967d9e59aa303dacacdc072373a1ac3f532614bacd283c927 |
| this file at commit | repo | recorded in run log |

## 6. Order of operations (binding)

1. Files-checks complete: `results_fp.json` prompt identity; §5.1 LLM-arm operating point; weak-model numbers; prompt-text pinning for this register.
2. TBDs above filled; this file committed and pushed; commit hash recorded.
3. Generation: clean set, then injected set, at the stated seeds.
4. Near-duplicate check.
5. Scoring: cells (a) through (e) on both sets, plus the mechanical arm.
6. Results and run log committed. Then, and only then, v8.3 drafting begins.
