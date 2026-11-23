# Proposal Creation SOP

Proposals must be grounded in observed code and executable evidence.

1. Inventory the relevant files, routes, entry points, tests, local data, and external services.
2. Label statements Verified, Inferred, Proposed, or Blocked.
3. State goals, non-goals, local/hosted release profile, privacy boundary, and supervision boundary.
4. Trace first run, normal success, missing configuration, source failure, login/CAPTCHA, cancellation, retry, duplicate, and recovery paths.
5. Give direct injection locations: file, function/route/component, before/after behavior, example payload/config/UI copy, and verification.
6. Cover authentication, CSRF, tenant ownership, path safety, executable profiles, resume/form data, rate limits, and logs.
7. Specify deterministic tests separately from live provider smoke tests.
8. Include rollout, rollback, documentation changes, unresolved decisions, and release gates.
9. Every open decision keeps a stable ID (`JH-D0N`, or a proposal-scoped prefix such as `JHD-REDESIGN-D0N`). Its simple cell holds only `**Question:** <one plain sentence?> **Suggested:** <one to three words>`. Keep all choices, recommendations, context and full reasoning in a same-document section headed `Reasoning for <ID>`; follow the [docs skill](../.claude/skills/docs/SKILL.md#decisions-two-tiers-in-the-owning-document) for the current policy and template. Classify strategic choices against all related public proposals and dependencies; technical methods do not override owner reservations. Record answers under the same ID, preserving prior wording and source mappings. Open repo-wide decisions remain in `docs/GAP_AUDIT.md` → Open decisions. Classification and a suggested answer approve nothing.

Use [the proposal template](proposals/TEMPLATE_PROPOSAL.md). A proposal is incomplete if a developer must guess where a change belongs or how failure/recovery behaves.
