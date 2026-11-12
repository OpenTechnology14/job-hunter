# Auto Applied vs User Applied in the Apply column (JH-D07)

| Field | Value |
|---|---|
| Status | Accepted and implemented 2026-11-09 (WM-JH-D07-IMPL-01) |
| Date | 2026-11-09 (supersedes the 2026-11-08 "Reviewed vs Done" draft, now a [deprecation stub](2026-11-08-reviewed-vs-done.md)) |
| Author | Agent (T3 rows WM-JH-D07-TERM-FIX-01, WM-JH-D07-IMPL-01) |
| Relates to | `docs/GAP_AUDIT.md` JH-D07; `PROPOSAL_RELEASE_AND_SAFETY_GAP_CLOSURE.md` §7.1 (GAP-JH-06) |
| Hub tokens or components touched | none (local only) |
| Surface | `apply_status.py` (new), `browser_apply.py`, `local_sync.py`, `sheets_sync.py`, `quality_filter.py`, `admin/server.py`, `admin/static/index.html` |
| Release profile | Local single-user |

## Problem

**Verified (before the change):** every application Job Hunter recorded was marked **Done**. It wrote Done both when it clicked Submit itself (Easy Apply, through `SubmissionGuard`) and when it only pre-filled a form that you then finished in the browser. The two cases couldn't be told apart.

## Decision (locked by the owner, 2026-11-09)

Two values replace Done:

| Label (shown, stored in the CSV) | Enum value | Meaning |
|---|---|---|
| **Auto Applied** | `auto_applied` | Job Hunter clicked Submit itself, through its guarded click |
| **User Applied** | `user_applied` | Job Hunter prepared the application (navigated, filled fields, attached the resume), and you clicked Submit by hand |

The old terminology ("Done" for these cases, "Reviewed") is retired.

## Trigger (detection point)

| Path | Recorded |
|---|---|
| Easy Apply: `SubmissionGuard.submit_once` clicked Submit | **Auto Applied** |
| Form fill / resume upload: Job Hunter pre-filled; you answer **y** to "Did you submit it yourself in the browser?" | **User Applied** |
| Form fill: you skip or say no | not marked |
| Manual ("apply in the browser"; Job Hunter didn't prepare anything) | not marked (existing behavior, distinct case) |
| Dry-run, skip, page changed, error | not marked |

`apply_to_job` returns the outcome (`auto_applied` / `user_applied` / not applied), and `run_apply_session` passes it to `mark_applied(..., status=...)`.

## Migration of existing rows

Historical rows can't be told apart after the fact, so the default is **Auto Applied**.

- Every `Done…` value becomes **Auto Applied**.
- Rows whose `Apply Method` isn't Easy Apply might really have been finished by hand. They're **also** tagged `needs-review` in `Notes`, a one-time sweep, so you can recheck them.
- No row is removed or reordered; the only fields changed are Apply and that Notes tag.
- Run it with `python apply_status.py --profile <name> --migrate [--dry-run]`. It's idempotent. Until you run it, readers already treat `Done…` as Auto Applied, so the UI, stats and protection rules are correct either way.

## Interaction notes (UI)

- **Apply column:** **Auto Applied** is a green, filled badge; **User Applied** is a blue, outlined badge. The text differs too, so color isn't the only signal.
- **Status pill and filter:** both count as "applied". Stats report `applied` (both) plus `auto_applied` and `user_applied` separately.
- **Protected-row rules** (stale cleanup, quality retro-clean) treat both values like the old Done: never auto-removed.
- **Google Sheets mode:** writes `✅ Auto Applied` / `✅ User Applied` instead of `✅ Applied`.

## Tests

- Easy Apply's guarded click records Auto Applied.
- A pre-filled form plus a "y" answer records User Applied; a "no" answer records nothing.
- The migration keeps every row (count, order, other fields) and tags only the ambiguous ones.
- Readers classify old `Done` as Auto Applied; protected-row rules hold for both values.

## Out of scope

OpenTech status sync, restructuring the Sheets columns, and hosted mode (JH-D01).
