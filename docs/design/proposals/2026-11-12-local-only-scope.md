# Local-only Job Hunter: what dropping hosted mode means (JH-D01 scope)

| Field | Value |
|---|---|
| Status | Draft for decision. **JH-D01 is not decided**; nothing here is implemented |
| Date | 2026-11-12 |
| Author | Agent (T3 row WM-JH-D01-SCOPE-01) |
| Relates to | `docs/GAP_AUDIT.md` JH-D01 (also JH-WP6); JH-006/008/009/011; `PROPOSAL_RELEASE_AND_SAFETY_GAP_CLOSURE.md` §4 and §11 |
| Hub tokens or components touched | none |
| Surface | `admin/server.py`, `admin/static/index.html`, `DEPLOY.md`, README, setup docs |
| Release profile | Local single-user (this doc describes removing the other one) |

## Problem

**Verified (main `444c7ea`):** Job Hunter has two release profiles in one codebase. *Local* is supported. *Deployed* is switched on by `--deployed` or `DEPLOYED=1`. It changes the admin UI in 9 places (expandable per-user sections, an add-user wizard, global stats), and `DEPLOY.md` Part 3 documents putting it on a public server (VPS with nginx basic auth, Docker, PythonAnywhere).

The audit's verdict is that deployed mode is **not safe to host**. It has no application auth or per-user isolation (JH-006), profiles are executable Python (JH-008), uploads are only partly validated (JH-009), and there's no production WSGI path (JH-011). JH-D01 asks whether to drop it or build all of that. This doc spells out the **drop** option, the recommended one, so the owner can see exactly what changes.

## Proposal: "local-only" defined

Job Hunter is a tool **one person runs on their own computer**. The trust boundary is that computer's user account.

| Area | Local-only means | Today |
|---|---|---|
| Network | The admin panel listens on loopback only (`127.0.0.1:5175`). There's no supported way to expose it, and the docs never describe a public URL | Already loopback-only in code; `DEPLOY.md` documents proxying it to the internet |
| Users | One operator. Several *profiles* (people you help) can still live in one install, all managed by that operator | Same, plus a "deployed" multi-user framing |
| Auth | No login. The OS account is the boundary; Origin allow-list plus single-use CSRF tokens stop other web pages from driving the panel | Origin + CSRF shipped (#13, #15) |
| Profiles | Trusted local data the operator edits. Executable `.py` profiles stay acceptable because no untrusted person can supply one | Same; JH-008 only matters for hosting |
| Data | Filesystem with atomic, locked writes; nothing leaves the machine except job-board requests and the user's own browser activity | Shipped (JH-010) |
| Apply | Visible browser and per-submit confirmation (SubmissionGuard); Auto Applied / User Applied | Shipped |

### What would change if JH-D01 = "drop"

1. **Code:** remove the `DEPLOYED_MODE` flag and the deployed-only UI branches, *or* keep the multi-profile overview as a plain local feature (see JH-D01-A). `/api/mode` goes away or always returns local.
2. **Docs:** remove or archive `DEPLOY.md` Part 3 (VPS, Docker, PythonAnywhere) and the README "Hosting / Deployment" section. `ADMIN_ALLOWED_ORIGINS` stays, for people who open the panel at a different local address.
3. **Gaps:** JH-006, JH-008, JH-009 (hosted parts) and JH-011 (WSGI half) close as **not applicable: release profile removed**. JH-007's local layers stay.
4. **Optional hardening (JH-D01-C):** refuse requests whose `Host` isn't loopback, which blocks DNS-rebinding reads as well as writes.

### What it does not change

Scraping, matching, the spreadsheet workflow, multi-profile support, the OpenTech integration plan (still a local runner that pushes sanitized metadata), and every safety rule in `AGENTS.md`.

## Data flow

| Datum | Source of truth | Shown where | Local or cloud | Notes |
|---|---|---|---|---|
| Profiles, resumes, form answers, history | `profiles/`, `output/{profile}/` | Admin panel, CLI | Local | Unchanged; never uploaded |
| Job postings | Job-board APIs | Spreadsheet, admin panel | Fetched over the network, stored locally | Unchanged |

## Interaction notes

- The admin header loses the "DEPLOYED" badge. If JH-D01-A keeps the overview, the per-user cards remain under a neutral name ("All profiles").
- Copy register: plain. Don't call the panel a "server" people can share.

## Accessibility

No visual change beyond removing a badge.

## Open questions

- [ ] **JH-D01** **Question:** Should Job Hunter drop its multi-user "deployed" mode and stay a local, single-user tool? **A. Yes, drop it (recommended):** fastest safe release; four hosted gaps become not applicable. **B. No, keep it:** auth, per-user isolation, declarative profiles, upload limits and a production server must be built first.
- [ ] **JH-D01-A** (only if A) **Question:** Keep the multi-profile overview (all profiles on one screen) as a local feature? **A. Yes, keep it, renamed "All profiles" (recommended):** useful for helping several people from one machine; costs nothing. **B. No, remove it with deployed mode.**
- [ ] **JH-D01-B** (only if A) **Question:** What happens to the hosting instructions in `DEPLOY.md`? **A. Move them to `docs/archive/` with a "not supported" banner (recommended):** keeps history, stops anyone following them. **B. Delete them.**
- [ ] **JH-D01-C** (only if A) **Question:** Also reject requests whose Host isn't `localhost`/`127.0.0.1`? **A. Yes (recommended):** blocks DNS-rebinding reads; no effect on normal use. **B. No, Origin + CSRF are enough.**

## Decision gates

| Gate | Decision needed | Decided by | Evidence required | State |
|---|---|---|---|---|
| G1 | JH-D01 | Owner | This doc | open |
| G2 | JH-D01-A/B/C | Owner | G1 = A | open |

## Out of scope

Building the hosted track (that's option B of JH-D01 and needs its own proposal), and changing how profiles are stored.

## Next steps

The owner answers JH-D01. If it's A, one PR implements the removals plus the A/B/C choices and closes the hosted gaps.
