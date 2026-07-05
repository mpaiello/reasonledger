# Reasonledger

A notation for transferring reasoning between AI systems that leaves an auditable record of the transfer.

Reasonledger encodes model-to-model messages as named blocks, each carrying an explicit instruction for how the receiver should process the enclosed content — activate this as a premise, enforce this as a constraint, verify this derivation step by step. Across a multi-hop chain of agents, those blocks and a three-way epistemic status accumulate into an inspectable record of what each model claimed, what it verified, and what it accepted on trust. That record is the ledger.

Reasonledger is a payload format. It rides inside a transport such as MCP or A2A; it does not replace one. It is **not** a blockchain and involves no tokens, chain, or consensus — "ledger" refers to the audit trail the format produces, nothing more.

## Why it exists

Multi-agent systems are easy to run and hard to inspect. When a planner hands work to an executor, and that output feeds a third agent, the reasoning that produced the final answer is scattered across opaque messages. Plain prose loses structure at each hop; plain JSON carries data but no record of what was checked versus assumed. Reasonledger keeps the structure and adds the record: which agent asserted what, which steps were verified, which were trusted, and where a claim's status changed along the way.

The intended use is governance and observability for agentic pipelines — a reasoning ledger you can read after the fact to see how a conclusion was reached and how much of it was actually verified.

## What's in the format

- **Content blocks** — `@FORMAL`, `@LOGIC`, `@DERIVE`, `@TAXONOMY`, `@ANCHOR` — typed reasoning with per-block processing instructions.
- **Exchange blocks** — `@STATE`, `@VERIFY`, `@OUTPUT` — state handoff, per-step verification reporting, response shaping.
- **Transfer-protocol blocks** — `@PROVENANCE`, `@TRANSFER_REPORT`, `@DERIVATION_TRACE`, `@SCOPE`, `@CONFIDENCE`, `@TRUST_TRANSFORMATION` — chain-of-custody, per-hop integrity, and trust calibration for multi-hop chains.
- **Three-way epistemic status** — `confirmed` / `open` / `denied`, preserved across model boundaries rather than collapsed.

Full grammar and processing rules are in [`SPEC.md`](./SPEC.md).

## A small example

```
@FORMAL [kepler_third]
T² = (4π² / GM) · a³

@DERIVE [circular_velocity]
(1) For a circular orbit, gravity supplies centripetal force
(2) GMm / r² = m v² / r
(3) From (2): v² = GM / r
→→ v = sqrt(GM / r)

@TAXONOMY [orbit_properties]
bound_orbit: confirmed
exact_eccentricity: open
parabolic_escape: denied
```

After a transfer hop, the receiver's record carries the audit trail:

```
@PROVENANCE [chain]
  hop_1: model_A → model_B | loaded+full_verify
@VERIFY [§circular_velocity]
(1): holds
(2): holds
(3): holds
→→: holds
```

## Reference validator

A small, dependency-free Python validator checks a document against the v1.0 grammar (recognized block types, the required `basis` attribute on `@LOGIC`, valid status markers, reference syntax):

```
python reference/validator.py examples/orbital.rl
```

It exits non-zero and prints line-referenced errors on any violation. The validator is reference code under Apache 2.0.

## Status

The format has been exercised in author-run experiments across five model architectures, where all five adopted the notation in their own output and preserved the three-way epistemic status across multi-hop transfer. These are author-run results; independent replication is invited and has not yet been performed. Reasonledger makes no claim about model cognition.

## Licensing

- **Specification and documentation:** [CC BY 4.0](./LICENSE).
- **Reference code:** [Apache 2.0](./LICENSE-APACHE).

Reasonledger is an open, royalty-free standard with no patent encumbrance. It is freely implementable by anyone, including in commercial products.

## Citing

See [`CITATION.cff`](./CITATION.cff). Short form:

> Aiello, M. P. (2026). *Reasonledger: Specification v1.0.* Zenodo. https://doi.org/10.5281/zenodo.19874728

## Lineage

Reasonledger was developed and first disclosed as **AI-Native Notation (ANN)**. The earlier name is retained in the provenance record for citation and priority; see [`NOTICE`](./NOTICE) and Section 13 of the specification.
