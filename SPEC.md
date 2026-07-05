# Reasonledger
## Specification v1.0

**Status:** Public standard release. Open and royalty-free.
**Originator:** Michael Patrick Aiello (ORCID 0009-0009-1429-9844)
**Canonical repository:** github.com/mpaiello/reasonledger
**Archive / DOI:** Zenodo concept-DOI 10.5281/zenodo.19874728
**Specification license:** CC BY 4.0. **Reference-code license:** Apache 2.0.
**Date:** 2026-06-30

---

## Abstract

Reasonledger is a notation for transferring reasoning between AI systems that leaves an auditable record of the transfer. Each construct is a named block carrying an explicit processing instruction that tells the receiving model what to do with the enclosed content, not only what the content is. Across a multi-hop chain, the transfer-protocol blocks and a three-way epistemic status (confirmed, open, denied) accumulate into an inspectable ledger of what each model claimed, what it verified, and what it accepted on trust. The format is architecture-independent and uses content-based named references that survive transfer. Reasonledger is a payload format designed to travel inside a transport such as MCP or A2A, not to replace one.

Reasonledger was developed and first disclosed as the notation AI-Native Notation (ANN); that lineage is retained for citation and priority (see Section 13).

---

## 1. Motivation

Two options dominate model-to-model communication today, and each loses something.

Natural language preserves meaning but introduces ambiguity, drops structural relationships during interpretation, and forces the receiver to reconstruct the sender's reasoning from prose. Structured data such as JSON preserves relationships but carries no processing semantics: the receiver still has to infer what operation each field implies.

Reasonledger is a third option. It keeps the structural precision of a typed format and adds, to each block, an explicit instruction for how the receiver should process the enclosed content. A premise block says "treat this as established, do not re-derive." A constraint block says "enforce this as an invariant for everything that follows." A derivation block says "verify each step, and report which step fails if one does." The processing semantics travel with the content.

This matters most in multi-hop chains, where content passes through three or more models in sequence and small interpretation errors compound at each boundary.

Reasonledger adds a second property the alternatives lack. Because each block records what operation was performed, and each transfer records what survived, a completed exchange is not only a result but a record of how the result was reached: which model asserted what, which steps were verified, which were accepted on trust, and where a claim's status changed across hops. That record is the ledger the format is named for, and it is the property that distinguishes Reasonledger from a plain message format. It is intended to complement observability and governance tooling for multi-agent systems, not to compete with a transport.

## 2. Design principles

- **Embedded processing instructions.** Every block type maps to a defined operation the receiver performs on the enclosed content.
- **Architecture independence.** The notation uses standard Unicode mathematics, standard predicate-logic symbols, and plain-text structure. Any model capable of mathematical reasoning, logical inference, and step verification can process it.
- **Named, content-based references.** Blocks reference one another by label, not by position, so references survive reordering and transfer across models.
- **Explicit epistemic status.** Classifications carry one of three markers — confirmed, open, denied — and the distinction is preserved rather than collapsed.
- **Additive and backward-compatible.** Later blocks extend the format without breaking earlier documents.

## 3. Base blocks

Reasonledger defines five content blocks and three exchange blocks. Examples below use neutral technical content (orbital mechanics, standard mathematics) to illustrate form, not subject matter.

### 3.1 Content blocks

#### @FORMAL — mathematical relationship
A structural fact in standard notation, to be recognized and held as an active premise.

**Processing instruction:** Activate existing knowledge of this relationship as a premise. Do not re-derive.

```
@FORMAL [kepler_third]
T² = (4π² / GM) · a³
```

#### @LOGIC — constraint
A predicate-logic constraint that binds all subsequent reasoning for the session. Each @LOGIC block declares a required `basis` attribute (see 4.7).

**Processing instruction:** Enforce as an invariant. Any later step that violates an active constraint is invalid.

```
@LOGIC [energy] basis: AXIOM
∀S: closed(S) → d/dt E(S) = 0
```

#### @DERIVE — derivation chain
A sequence of steps, each following from prior steps or from active @FORMAL / @LOGIC blocks. The chain terminates at a forced conclusion (→→).

**Processing instruction:** Step through in order. Check each step against active premises and constraints. If the chain holds, accept the conclusion. If a step fails, report which step and why.

```
@DERIVE [circular_velocity]
(1) For a circular orbit, gravity supplies centripetal force
(2) GMm / r² = m v² / r
(3) From (2): v² = GM / r
→→ v = sqrt(GM / r)
```

#### @TAXONOMY — classification with epistemic status
Key-value classifications, each carrying a three-way status marker: confirmed (supported by a completed derivation), open (genuinely undetermined), denied (explicitly excluded).

**Processing instruction:** Store as structured data. Preserve all three categories. Do not collapse open into confirmed or denied.

```
@TAXONOMY [orbit_properties]
bound_orbit: confirmed
orbital_period_known: confirmed
exact_eccentricity: open
parabolic_escape: denied
```

#### @ANCHOR — context
Minimal natural-language text that binds notation to operational meaning.

**Processing instruction:** Read once for orientation. Do not dwell; proceed to the next formal block.

```
@ANCHOR
[S denotes any gravitationally bound two-body system. The derivations
are independent of the bodies' composition.]
```

### 3.2 Exchange blocks

#### @STATE — processing-state declaration
A declaration a model generates for onward transmission, capturing where its processing stands so a receiver can resume from that point. It records active constraints, completed derivations and their conclusions, items recognized during processing, and unresolved questions.

**Processing instruction (generator):** Report honestly what is active, completed, recognized, and unresolved.
**Processing instruction (receiver):** Load the state. Distinguish what the sender verified from what the sender accepted on trust.

```
@STATE
active_constraints: [@LOGIC[energy]]
completed: [§circular_velocity]
recognized: orbit is bound under the stated premises
unresolved: eccentricity (open)
```

#### @VERIFY — verification request
A request to check a derivation and report per-step results using three result codes: holds, fails, uncertain.

**Processing instruction:** Run the verification. Report per-step results with reasons. Do not argue for or against the derivation; verify it.

```
@VERIFY [§circular_velocity]
Check steps (1)-(3) and →→ against active @FORMAL and @LOGIC blocks.
Report per step: holds | fails | uncertain — reason
```

#### @OUTPUT — response-format specification
Specifies how the receiver should structure its response. The `mode` field takes one of: report, derive, defend, verify, extend. Optional fields name which blocks to include and which notation to use.

```
@OUTPUT
mode: report
include: [@STATE, @VERIFY[§circular_velocity]]
```

## 4. Transfer-protocol blocks

For multi-hop chains, Reasonledger defines six transfer-protocol blocks plus one required attribute on @LOGIC. These maintain chain-of-custody, degradation tracking, and trust calibration as content passes through successive models. They appear in responses and transfer records rather than in source documents (except @SCOPE, which may appear in both).

### 4.1 @PROVENANCE — chain-of-custody
Append-only record. Each hop appends its entry (source model, target model, action taken, trust summary, timestamp). Prior entries are never modified.

```
@PROVENANCE [chain]
  hop_1: model_A → model_B | loaded+full_verify
  hop_2: model_B → model_C | loaded+partial_verify
```

### 4.2 @TRANSFER_REPORT — per-hop degradation
Records structural integrity, content preservation, epistemic degradation, and new unresolved items for a single hop.

### 4.3 @DERIVATION_TRACE — per-derivation provenance
Tracks, for each derivation, the steps claimed by the source, the steps actually present in the received state, completeness (full / summary-only / conclusion-only), and reconstruction status.

### 4.4 @SCOPE — validity boundary
Declares what falls inside and outside a derivation's validity, with an enforcement rule (default: claims outside scope are out-of-scope, not wrong).

### 4.5 @CONFIDENCE — multi-axis trust
Replaces single-value confidence with a structured assessment across independent axes: structural (does the conclusion follow from the premises), empirical (does it match known behavior), transfer (how much source verification survived).

### 4.6 @TRUST_TRANSFORMATION — trust history
Append-only record of how a trust label changes across hops (for example, verified becoming loaded) and the reason for each change.

### 4.7 @LOGIC `basis` attribute
Every @LOGIC block declares its epistemic ground: AXIOM (true by definition), DERIVED (follows from prior premises), or EMPIRICAL (grounded in observation). This prevents a downstream model from treating a derived constraint as axiomatic, or an empirical observation as definitional.

## 5. Cross-reference system

References are by label, so they survive transfer:

- formal premise: `@FORMAL[label]`
- constraint: `@LOGIC[name]`
- derivation: `§name`; a specific step: `§name(N)`
- classification: `@TAXONOMY[name]`
- scope: `@SCOPE[name]`
- confidence: `@CONFIDENCE[§name]`

## 6. Processing order

Source documents are processed in this order:

1. @FORMAL — activate premises
2. @LOGIC — enforce constraints (with basis verification)
3. @SCOPE — establish validity boundaries
4. @DERIVE — execute derivations within scope
5. @TAXONOMY — store classifications with status markers
6. @ANCHOR — read for context as encountered
7. @OUTPUT — structure the response last

@STATE, @VERIFY, and the transfer-protocol blocks appear in responses and transfer records, not in source documents.

## 7. Architecture independence

The notation relies only on standard Unicode mathematics, standard predicate-logic symbols (∀, ∃, →, ∧, ∨, ¬), plain-text structure, and named references. It assumes no markup language and no model-specific tokens. Any model capable of mathematical reasoning, logical inference, step verification, and structured output can both read Reasonledger and produce it.

## 8. How this specification was developed

Reasonledger's grammar was not designed top-down by a committee. It was developed empirically. Structured content was transmitted across several language model architectures, and the structural extensions that multiple architectures proposed independently were promoted into the specification; extensions proposed by only one architecture or in only one content domain were documented but not promoted.

A structural extension is promoted to the core specification when it meets all three of the following:

1. it appears independently in at least two different content domains;
2. it appears independently in at least two different model architectures;
3. it addresses a structural need not already served by existing blocks.

The six transfer-protocol blocks in Section 4 and the @LOGIC `basis` attribute were promoted under this method. This keeps the specification general across architectures rather than fitted to any one model's tendencies.

Reasonledger was developed through human-directed, AI-assisted work; the specification and its validation were produced in collaboration with a large language model (Claude, Anthropic). This is disclosed for transparency and does not affect the open, royalty-free terms under which Reasonledger is released.

## 9. Validation

The findings below come from author-run experiments. Independent replication is invited and has not yet been performed; results should be read accordingly.

In author-run testing across five architectures (Claude, Gemini, GPT-4o, DeepSeek, Grok):

- All five architectures adopted Reasonledger in their own output when given Reasonledger-encoded input, without being instructed to do so.
- The three-way epistemic status was preserved across multi-hop transfer without collapsing.
- Structural fidelity held across multi-hop transfer chains spanning multiple architectures, for content domains ranging from orbital mechanics to formal specifications.

These results characterize structural adoption and cross-architecture fidelity. They are not claims about model cognition, and no such claim is made or required.

## 10. Relationship to other work

Reasonledger occupies a specific position relative to neighboring work, and the boundaries are deliberate:

- **Transport and discovery protocols (MCP, A2A, and similar).** These standardize the message envelope, routing, and capability discovery; the payload is typically JSON. Reasonledger is a payload format that can sit inside such an envelope. It complements these protocols rather than competing with them.
- **Prompt compression and learned soft prompts.** These reduce token count, often tuned to a target model. Reasonledger is a fixed, human-readable, model-agnostic notation applied without per-model tuning; token economy is not its claim.
- **Agent communication languages (KQML, FIPA-ACL).** These define performatives for inter-agent messaging. Reasonledger's blocks specify processing operations on enclosed reasoning content and carry an explicit epistemic-status system; it is a content notation rather than a general agent-messaging language.

## 11. Version lineage

This public release consolidates internal development versions 0.1 through 1.1 into a single standard. One block present in development versions, a performative self-reference block (@TRIGGER), is excluded from this standard: its execute-on-read semantics matched a prompt-injection pattern, and it is omitted pending a trust-gated redesign. Implementations should not rely on it.

## 12. License and citation

The specification text is released under **Creative Commons Attribution 4.0 International (CC BY 4.0)**. Any reference implementation is released under the **Apache License 2.0**.

To cite this specification:

```
Aiello, M. P. (2026). Reasonledger: Specification v1.0.
Zenodo. https://doi.org/10.5281/zenodo.19874728
```

`CITATION.cff`:

```yaml
cff-version: 1.2.0
title: "Reasonledger: Specification v1.0"
message: "If you use this specification, please cite it as below."
type: standard
authors:
  - family-names: Aiello
    given-names: Michael Patrick
    orcid: "https://orcid.org/0009-0009-1429-9844"
version: "1.0"
date-released: "2026-06-30"
license: CC-BY-4.0
repository-code: "https://github.com/mpaiello/reasonledger"
doi: "10.5281/zenodo.19874728"
```

## 13. Provenance and open-standard statement

Reasonledger was originated by Michael Patrick Aiello and was developed and first documented under the name AI-Native Notation (ANN). A US provisional patent application (63/980,973) was filed on 2026-02-12, establishing an early, confidential priority record of the work; a provisional application is not a public disclosure. The first public disclosure of the specification was its publication in the canonical repository on 2026-04-28. This consolidated standard is dated 2026-06-30.

Reasonledger is released as an open, royalty-free standard. It is not encumbered by an enforced patent, and it is intended to be freely implementable by anyone, including in commercial products, under the licenses in Section 12. The provisional application is being allowed to lapse; the public record establishes both the authorship and the priority of the disclosure, and serves as defensive prior art so that the format remains open to all.

---

*Reasonledger Specification v1.0. Released 2026-06-30 under CC BY 4.0 (specification) and Apache 2.0 (reference code).*
