# Decision documentation backfill

**Status:** Documentation candidate; independent review pending. All product gates below remain open.
**Date:** 2026-11-22
**Release profile:** Local single-user; hosted remains unsupported pending its existing gate
**Evidence:** Verified source inventory and code reading; reasoning effects are Proposed, not executed product behavior.

## Outcome and authority

The owner authorized a documentation-only backfill of existing open decisions, their strategic/technical classification, and necessary intake/index/instruction metadata. This is the canonical public task note under the proposal SOP. It adds no product decision, implementation permission, release approval or priority queue. Codex wrote the candidate directly; independent Codex review is pending. No other writing agent or provider was used.

Success means a novice can answer each simple question, find complete reasoning in that same document, and recover every original option, recommendation and hold. The source baseline is `8100b23b4306037eeee9c91c511f991c25f5bff8` in this public repository. No predecessor history is imported.

## Verified landscape and inventory

18 unique open gates have 20 owning occurrences in five documents. Occurrences count actual questions owning a choice, not every ID reference, reasoning heading or release/test gate. Nine are strategic; nine are technical. All remain open and owner-reserved, including technical gates. JH-D01 has three occurrences with the same drop/secure semantics. Its three child gates are conditional on choosing drop; they are not answered or activated by this backfill.

The baseline contains 32 raw bold Question marker lines across ten Markdown files: 20 open owning occurrences, five resolved rows, one release pointer, and six instruction/example lines (the gap-table introduction, two skills, the SOP and two templates). Thus the older 28-line survey is not the current open-gate count. Searches of the remaining landscape found no extra owner choice without a Question marker; implementation/release evidence gates are excluded below.

| Owning document | Open gate IDs | Owning occurrences | Classification and reservation |
|---|---|---|---|
| [Gap audit](../GAP_AUDIT.md#open-decisions-owner) | JH-D01, JH-D02, JH-D05 | 3 | D01 strategic release scope; D02 technical dependency packaging, owner-reserved; D05 strategic merge-risk policy |
| [Local-only scope](../design/proposals/2026-11-12-local-only-scope.md#open-questions) | JH-D01, JH-D01-A, JH-D01-B, JH-D01-C | 4 | D01 and A strategic scope; B technical documentation handling; C technical request hardening; all owner-reserved |
| [Integration readiness](PROPOSAL_OPENTECH_INTEGRATION_READINESS.md#12-risks-and-unresolved-decisions) | JH-OT-D01, JH-OT-D02, JH-OT-D03, JH-OT-D04, JH-OT-D05 | 5 | D02 strategic privacy defaults; D01/D03/D04/D05 technical contract, outbox limits, secret storage, persistence; source API/privacy/maintainer/security owners retained |
| [Redesign](REDESIGN_FROM_OPENTECHAPP_PATTERN.md#7-decision-gates) | JHD-REDESIGN-D01 through JHD-REDESIGN-D07 | 7 | D01–D05 strategic investment, voice, layout, queue and marketing; D06/D07 technical instruction generation and contrast method; all explicitly owner-gated |
| [Release and safety](PROPOSAL_RELEASE_AND_SAFETY_GAP_CLOSURE.md#decision-jh-d01--disposition-of-deployed-mode) | JH-D01 | 1 | Same strategic release-profile gate as gap audit and local-only scope |

### Exclusions and retained state

- JH-D03/D04/D06/D07/D08 are answered/resolved; their complete gap-audit rows stay byte-identical. The accepted apply-status design and superseded Reviewed/Done stub stay unchanged. Withdrawn D07-A/B are not open gates.
- JH-WP6 is JH-D01. WP0–WP5 describe implementation and verification, not additional owner choices. The release proposal's second bold Question mention points to §4 and is not another gate.
- The standalone/template-testing proposal has unchecked scenario evidence, not unanswered product choices. Its live tests are not executed here.
- Audit/release checklists, route contracts, pressure-test scenarios, roadmap ideas and proposals' acceptance criteria are work/evidence gates, not automatically owner decisions. Dated claims about already closed safety work do not reopen those decisions.
- SOP, skill and proposal/design-template questions are instruction/examples, not gates. The new task note introduces none. ID references in other docs point to the owning gates and are not extra occurrences.

### Whole-proposal assessment

**Strategic:** Local/hosted disposition sets the supported trust boundary, but optional OpenTech coordination is still a local runner and does not require hosted admin. Admin investment (redesign D01), companion versus independent marketing (D05), and the replacement-template narrative interact: do not invest in a broad restyle or promise a delivered replacement based only on the public proposal's intent. The integration's privacy-default gate remains separate from choosing a review surface. Voice, layout and queue choices affect all proposal consumers and inbound links; they are not implementation permission for that landscape.

**Technical:** The API-version contract, bounded outbox, protected secret store, main persistence, dependency packaging, instruction generation, deployment-doc handling, Host validation and contrast method each concern how a bounded result is delivered. Their source owners still decide. Escalate a change to outbound fields, retention/data-loss acceptance, supported operating systems, spreadsheet editing, public generator scope, merged security instructions, hub-token adoption or supported access as a strategic boundary change.

**Readiness:** This documentation is ready for independent review, not a build release. Existing local safety code has source evidence: `SubmissionGuard.submit_once`, Auto Applied/User Applied outcomes, atomic writes/revisions, Origin validation, single-use CSRF, debug off and loopback binding. They are not re-tested here. Hosted auth/tenant/production-serving work remains held. Integration stays proposed, optional and sequenced after WP1–WP4; the sanitizer fixture must not guess the two blocked default fields. Layout/queue/generation/marketing/style remain at their existing gates. No proposal is promoted to Accepted or funded by classification.

**Public cross-project implications:** Only this repository's existing public integration/redesign/pointer descriptions establish the OpenTech API/template owner and hub dependencies. Their current delivery and hub approvals are not freshly verified here; no private content is used as public evidence. This task changes only Job Hunter documentation and instructions. It grants no work in another repository.

## Policy, wording and source conflicts

The [current decision policy](https://github.com/OpenTechnology14/AgentWorkflows/blob/3d815cbd043e05c8df4579206d6a2d61182cbb48/workflows/DECISIONS.md) and [template](https://github.com/OpenTechnology14/AgentWorkflows/blob/3d815cbd043e05c8df4579206d6a2d61182cbb48/templates/DECISION_GATE.md) require the third shape dated 2026-11-17. The accepted workflow reference predates that policy and has no DECISIONS file; a read-only reference check reported upstream drift, with accepted local hashes unchanged. This task applies the explicitly requested current policy without changing workflow pins, adapters, configuration or generators.

All 20 simple questions were rephrased to remove lookup terms, paths, identifiers, embedded options or unexplained abbreviations and keep one novice-answerable sentence. The full original wording/options remain verbatim after the Context label in each reasoning section. Short Suggested words name the retained recommended choice. In the gap table, which has no recommendation column and contains immutable closed rows, Context explicitly labels the short suggestion as the author's presentation of the recorded source recommendation. Integration/redesign tables gain a Default column preserving the source recommendation. None is a new owner answer.

**Representation exception, explicitly authorized for this backfill:** Redesign D01/D03/D04/D05/D06 already have different lower-case Options keys and uppercase Question keys. The original Options cells stay byte-identical, and original uppercase choices remain verbatim in Context. Reasoning follows existing uppercase Question A/B keys; omitted choices are appended in that reasoning sequence while explicitly retaining their original lower-case source key beside their exact meaning. This sequence is a presentation convention, not a changed source answer key. A letter-only answer without its source version requires clarification; no historical answer is normalized. Independent review must assess the mappings semantically against the baseline.

- Dependency D02 retains source (c), optional extras, although the old question listed only A/B.
- Redesign D01 retains source (c), undecided/hold 11–12; D04 retains original (b), registry plus audit, and original (c)/Question B, keep-index. D03/D05/D06 retain both conflicting key sets as well.
- No gate has more than four distinct source choices in this inventory. For future larger source sets, retain all and declare a representation exception rather than drop/group/reletter them.
- The release proposal's broad hosted-gap closure claim differs from the newer local-only scoped not-applicable closure; both remain labelled in D01 reasoning. Removing hosted scope does not remove existing local safety protections.
- Older prose says no CI/atomic writes/CSRF, and release goals use earlier outcome names. Current code and the gap audit contain later evidence; the dated text remains historical. The proposed deployed-startup refusal still does not exist in code. Redesign says pointer/register absent while the later pointer exists. Contrast ratios are historical source measurements, not a new measurement. The explicit D07 method gate remains despite prose saying items 1–5 need no decision.

## Direct documentation map and failure handling

| Surface | Before | Candidate | Verification |
|---|---|---|---|
| Five owning docs above | Choices mixed into questions; no full same-doc tiers | Plain question plus Suggested, classified complete option reasoning | Inventory, shape, source-preservation and resolved-row checks |
| Docs/design skills, SOP, two templates | Old inline-options instructions | References to full third-shape policy, source/answer preservation and reservations | Local link/fragment and instruction review |
| This note and documentation index | No public scoped backfill record | Canonical authority, landscape, exceptions and review state | Index/link and public-content scan |

Missing evidence stays Unknown with the measurement, fixture or owner contract that would settle it. A malformed question, omitted source choice, ambiguous key or disagreement with a recommendation is a review failure, not a guessed answer. Runtime failure paths, retries, uploads and submission state are unchanged. No profiles, resumes, credentials, output, browser or live provider are loaded. Rollback is a documentation revert that preserves actual owner answers and resolved history.

## Validation and next handoff

Local documentation checks cover whitespace (including new files), question purity, eight-field order, same-document reasoning, source cells/options/recommendations, classification/count parity, local links/fragments, public-content boundaries and unchanged runtime/holds. Representative failure inputs must be rejected by the local check aid. There is no existing project documentation checker or active pre-push hook; checks are supplied outside the repository for this review. Application CI/install/product/live tests are omitted under the root docs-only verification policy. No CI-green claim is made.

**Executed on the candidate:** the outside-repository documentation aid passed 280 assertions with zero errors: 18 unique gates, 20 occurrences, 9 strategic/9 technical; five resolved rows and all pre-Question source cells preserved; local targets/fragments valid; only the twelve scoped Markdown paths changed. Negative controls rejected trailing context, pre-cell labels, missing Suggested, code in a question, a second question mark, excess words, a missing option/field/trade-off heading/suggestion mark and missing worst-case section. `git diff --check` passed; the aid separately checked whitespace in the new task note. Source reading found no tracked Python import of fpdf2, and confirmed the current guard/status/atomic/admin symbols named above without importing application code. This is local documentation evidence, not an independent review or a product-test result.

**Bounded repair after the first independent review:** that review requested two semantic repairs. JH-D01-C now asks about requests addressed back to the very same computer, replacing the website-versus-local-address distinction; the exact source allow-list and owner reservation are unchanged. All ten integration Money fields now distinguish each option's incremental purchases from the shared optional-connection cost. Remaining unknowns name field-volume/billing, outbox-capacity, adapter-license/platform or migration-space evidence as applicable; no price, provider or paid dependency is assumed. The original 280 assertions pass again. A separate repair check verifies that only these question/name references, ten Money lines and this factual task-note entry differ from the first candidate. This is the writer's repair response, not an independent PASS; review remains pending.

Next: independent reviewer inspects the exact baseline-to-candidate commit diff, semantic option fidelity, novice wording, unknown evidence and representation exception. Any findings return to the sole writer. Push and PR creation wait for independent PASS and parent authorization; merge is excluded. This note's review state remains pending until that evidence exists. No user-visible behavior or project log entry is claimed; PR trailer: `Logs: none.`
