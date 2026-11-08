# Reviewed vs Done in the Apply column (JH-D07)

| Field | Value |
|---|---|
| Status | Draft (decision-ready; not implemented) |
| Date | 2026-11-08 |
| Author | Agent (T3 row WM-JH-D07-SCOPE-01) |
| Relates to | `docs/GAP_AUDIT.md` JH-D07; `PROPOSAL_RELEASE_AND_SAFETY_GAP_CLOSURE.md` §7.1 (GAP-JH-06) |
| Hub tokens or components touched | none (local only) |
| Surface | `browser_apply.py`, `local_sync.py`, `sheets_sync.py`, `admin/server.py`, `admin/static/index.html` |
| Release profile | Local single-user |

## Problem

**Verified (main `60378c0`):** `handle_form_apply` returns success when you press Enter after reviewing a generic form. `run_apply_session` then calls `mark_applied`, which writes `Apply = "Done"` (`local_sync.py`) or `"✅ Applied"` (`sheets_sync.py`). So "Done" today means either that Job Hunter clicked Submit through `SubmissionGuard` (Easy Apply), or that Job Hunter filled a form and you said you were finished. It may not have been submitted at all. §7.1 says manual review is never recorded as submitted.

## Proposal

Add one Apply value, **`Reviewed`**: Job Hunter prepared the application (navigated, filled fields, attached the resume), but did **not** click Submit itself. **`Done`** keeps its name and narrows to "Job Hunter observed its guarded Submit click succeed." Nothing else about the Apply column changes.

## Trigger

| Path | Today | Proposed |
|---|---|---|
| Easy Apply, guarded Submit clicked | Done | **Done** |
| Generic form / resume upload, you press Enter | Done | **Reviewed** |
| Manual ("apply in the browser") | not marked | not marked (unchanged) |
| Skipped (`s`), dry-run, page changed, error | not marked | not marked (unchanged) |

Implementation shape: `apply_to_job` returns an outcome (`submitted` / `reviewed_manual` / `skipped` / `failed`, per §7.1) instead of a bool. A new `mark_reviewed()` sits beside `mark_applied()` in both storage backends.

## Data flow

| Datum | Source of truth | Shown where | Local or cloud | Notes |
|---|---|---|---|---|
| Apply value | `output/{profile}/jobs.csv` `Apply` (or Sheets col H) | Jobs table, status pills, stats, all-users | Local (Sheets if configured) | Values: blank / `Y` / `N` / `Reviewed` / `Done` |
| Date Applied | same row | Jobs detail | Local | Set for both Reviewed and Done |

## Migration of existing rows

Existing `Done` rows can't be told apart after the fact: the CSV doesn't record which path produced them. Options, as decision **D07-A**:

- **A1 (recommended): leave existing `Done` rows unchanged.** The new meaning applies from the next apply run. Nothing is rewritten.
- A2: relabel every existing `Done` as `Reviewed` (overstates caution; it hides real Easy Apply submissions).
- A3: relabel only rows whose `Apply Method` isn't Easy Apply (a heuristic; can be wrong both ways).

## Interaction notes (UI)

- **Apply column:** a new `Reviewed` badge, styled like `Done` but visually distinct (outlined, not filled), with the tooltip "Prepared by Job Hunter; you finished it". `Done` keeps its current filled badge.
- **Status pills / filter (`_classifyApply`):** a new `reviewed` bucket next to `applied`, shown as "Reviewed (n)".
- **Stats** (`/api/jobs/<p>/stats`, `/api/all-users`, AI-training counts): add a `reviewed` count. Keep `applied` as Done only.
- **Promote action:** on a Reviewed row, a "Mark as submitted" button sets `Done` (your explicit statement), through the existing conflict-checked PATCH.
- **Protected-row rules** (stale cleanup, quality retro-clean): treat `Reviewed` like `Done`, so it's never auto-removed.
- Copy register: plain and measured; no claim of submission unless Job Hunter saw it.

## Accessibility

The badge difference must not rely on color alone: different text plus an outline. It reuses existing text colors (contrast unchanged).

## Token and component impact

| Item | New, changed or deprecated | Hub change or local override | Why |
|---|---|---|---|
| `.apply-btn.reviewed` CSS | new | local | distinct badge |

## Tests (to write with the build)

Outcome mapping per path (fake page), `mark_reviewed` in both backends, migration option behavior, `_classifyApply` buckets, stats counts, and protected-row rules for `Reviewed`.

## Open questions

- [ ] **D07** **Question:** Should a form you finish by hand be recorded as "Reviewed" instead of "Done"? **A. Yes (recommended):** Done then always means Job Hunter saw the submit. **B. No, keep marking them Done.**
- [ ] **D07-A** **Question:** What happens to jobs already marked Done? **A. Leave them as they are (recommended):** nothing is rewritten, and the new meaning starts with the next run. **B. Relabel them all Reviewed.** **C. Relabel only non-Easy-Apply ones.**
- [ ] **D07-B** **Question:** Add a "Mark as submitted" button on Reviewed rows? **A. Yes (recommended):** you confirm what Job Hunter couldn't see. **B. No.**

## Decision gates

| Gate | Decision needed | Decided by | Evidence required | State |
|---|---|---|---|---|
| G1 | D07, D07-A, D07-B | Owner | This doc reviewed | open |

## Out of scope

Typed outcomes beyond the Apply column (OpenTech status sync), Sheets column restructuring, and hosted mode.

## Next steps

Owner answers D07 / D07-A / D07-B. Then: one PR implementing the trigger, the storage functions, the UI and the tests above.
