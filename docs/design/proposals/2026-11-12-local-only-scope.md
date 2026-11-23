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

### JH-D01

**Question:** Should this tool drop shared online use and stay on one trusted person’s computer? **Suggested:** Local only
### JH-D01-A

**Question:** Should the screen showing all profiles remain available on one computer? **Suggested:** Keep overview
### JH-D01-B

**Question:** Should unsupported hosting instructions be archived or deleted? **Suggested:** Archive instructions
### JH-D01-C

**Question:** Should the panel accept only requests addressed back to the very same computer? **Suggested:** Same computer only

## Decision gates

| Gate | Decision needed | Decided by | Evidence required | State |
|---|---|---|---|---|
| G1 | JH-D01 | Owner | This doc | open |
| G2 | JH-D01-A/B/C | Owner | G1 = A | open |

## Out of scope

Building the hosted track (that's option B of JH-D01 and needs its own proposal), and changing how profiles are stored.

## Next steps

The owner answers JH-D01. If it's A, one PR implements the removals plus the A/B/C choices and closes the hosted gaps.

## Decision reasoning — documentation backfill, 2026-11-22

**Proposed:** The choices below remain open. Source recommendations are preserved; classification supplies no implementation or release approval. Historical option mappings are retained explicitly where they conflict.

### Reasoning for JH-D01

- **Context:** **Strategic; open, owner-reserved.** Chooses the supported release scope and security investment, across the safety proposal, local-only scope, optional integration and admin-future proposal. Source recommendation: original Question A; no answer is recorded by this backfill. The release proposal broadly says removing hosting closes JH-006 through JH-011; the newer local-only scope limits not-applicable closure to hosted parts (JH-006/008/009/011) and retains JH-007 local protections. Both dated statements remain; no gap is closed by this backfill. Code reading at the task base shows DEPLOYED_MODE still exists and main binds loopback; the proposed refusal to start is not implemented. JH-WP6 is this same gate, not another decision. Product constraints: [root safety and privacy rules](../../../AGENTS.md). Original question wording and options (verbatim, after its label): Should Job Hunter drop its multi-user "deployed" mode and stay a local, single-user tool? **A. Yes, drop it (recommended):** fastest safe release; four hosted gaps become not applicable. **B. No, keep it:** auth, per-user isolation, declarative profiles, upload limits and a production server must be built first. Original pre-question label: - [ ] **JH-D01** ; all conditional gates remain pending.
- **Prerequisites:** An explicit owner answer on the supported release profile; any implementation still needs its scoped proposal and verification.

#### Option A: Local only (Suggested)

- **What it is:** Remove/deprecate deployed mode and multi-user UI/API claims; retain loopback single-user admin. This is the source’s recommended drop option, not an action taken here.
- **Unlocks:** A supported local-only boundary; hosted gaps can become not applicable only after removal.
- **Blocks:** A supported hosted service from this codebase.
- **Risks:** Users may still need remote access; a later hosted proposal can restore that scope after all security gates pass. Likelihood is Unknown — operator remote-access requirements would establish unmet demand.
- **Effort:** Unknown — maintainer needs a removal/UI/docs breakdown plus the conditional scope answers to estimate duration.
- **Money:** None — this choice adds no paid service; implementation/review labor is covered by the unmeasured Effort above.
- **Incompatible with:** B (Secure hosting) as simultaneous choices for JH-D01.
- **Needs first:** Decide JH-D01-A/B/C before implementing the drop scope.

#### Option B: Secure hosting

- **What it is:** Retain deployed mode and implement the entire Hosted Track in §11 of the release/safety proposal. Keep hosting unsupported until every acceptance gate passes.
- **Unlocks:** A possible authenticated, isolated hosted service after verification.
- **Blocks:** The fastest release obtained by removing the hosted profile.
- **Risks:** Incomplete isolation could expose profiles or execute untrusted Python; stop exposure and require the full hosted test matrix before reopening. Likelihood is Unknown — a complete tenant-isolation, upload and session security test report would establish remaining exposure.
- **Effort:** Unknown — maintainer and security reviewer need a complete hosted-track design and test breakdown to estimate duration.
- **Money:** Unknown — the owner needs a priced plan for secure hosting, including the proposed connection or hosted service and support; this document enables no spend.
- **Incompatible with:** A (Local only) as simultaneous choices for JH-D01.
- **Needs first:** Auth, authorization, CSRF, declarative profiles, upload limits, safe persistence and production serving must all be designed and verified.

#### Trade-offs

| Axis | A (Suggested) | B |
|---|---|---|
| Supported audience | One trusted local operator | Multiple hosted users after security work |
| Release dependency | Removal plus local scope choices | Entire hosted security track |

- **Downstream impact:**
  - **Changes:** A changes admin mode/UI, DEPLOY and setup/release claims under the local-only scope; B changes the hosted surfaces in release/safety §11. Neither removes submission confirmation or local-private-data rules.
  - **Unblocks:** A unblocks removal planning and conditional JH-D01-A/B/C; B unblocks a separate hosted proposal, not a hosted release.
- **Cost of deferring:** Hosted disposition remains open; supported local work can continue under existing authority. No default answer is applied. Cost begins when work assumes hosted support or invests in hosted-only UI; timing is Unknown — a scoped work plan would settle it.
- **Worst case:** Dropping hosting proves too restrictive for intended users. Their unmet access need is the signal; retain the local release and propose the complete hosted track before restoring any exposure.

### Reasoning for JH-D01-A

- **Context:** **Strategic; open, owner-reserved.** Chooses retained local product scope when hosting is dropped; independent of whether the admin will later be replaced. Source recommendation: original Question A; no answer is recorded by this backfill. Original Question A keeps/renames “All profiles”; B removes it. Source says keeping it “costs nothing”; this is a source recommendation, not measured effort or a zero-cost implementation estimate. Product constraints: [root safety and privacy rules](../../../AGENTS.md). Original question wording and options (verbatim, after its label): Keep the multi-profile overview (all profiles on one screen) as a local feature? **A. Yes, keep it, renamed "All profiles" (recommended):** useful for helping several people from one machine; costs nothing. **B. No, remove it with deployed mode.** Original pre-question label: - [ ] **JH-D01-A** (only if A) ; all conditional gates remain pending.
- **Prerequisites:** JH-D01 = drop hosting, plus an explicit owner answer to this conditional gate.

#### Option A: Keep overview (Suggested)

- **What it is:** Keep the multi-profile overview as a local feature named “All profiles.” Profiles remain managed by one trusted operator.
- **Unlocks:** One screen for helping several people from one machine.
- **Blocks:** Removing every overview branch with deployed mode.
- **Risks:** The retained overview may still imply shared access; rename it and verify that copy and behavior remain local. Likelihood is Unknown — a novice walkthrough of the renamed overview would test expectations of shared access.
- **Effort:** Unknown — maintainer needs a deployed/local UI branch inventory and rename diff to estimate work.
- **Money:** None — this choice adds no paid service; implementation/review labor is covered by the unmeasured Effort above.
- **Incompatible with:** B (Remove overview) as simultaneous choices for JH-D01-A.
- **Needs first:** Separate local overview behavior from deployed-only framing.

#### Option B: Remove overview

- **What it is:** Remove the overview together with deployed mode. Keep existing per-profile local workflows.
- **Unlocks:** A smaller local admin surface.
- **Blocks:** The all-profiles-at-once workflow.
- **Risks:** Operators lose a useful overview; restore a local-only view later if evidence justifies it. Likelihood is Unknown — operator workflow feedback would establish the cost of losing the overview.
- **Effort:** Unknown — maintainer needs an overview-removal diff and profile-selection walkthrough to estimate work.
- **Money:** None — this choice adds no paid service; implementation/review labor is covered by the unmeasured Effort above.
- **Incompatible with:** A (Keep overview) as simultaneous choices for JH-D01-A.
- **Needs first:** Check all profile-selection paths remain usable without the overview.

#### Trade-offs

| Axis | A (Suggested) | B |
|---|---|---|
| Local view | All profiles together | Per-profile workflow |
| Removal scope | Keep and rename overview | Remove overview branches |

- **Downstream impact:**
  - **Changes:** admin/static/index.html and local admin wording differ by answer; multi-profile data support stays. Coordinate with redesign D01 before broader restyling.
  - **Unblocks:** The exact removal/UI slice under the local-only proposal.
- **Cost of deferring:** Conditional work waits for JH-D01; existing overview remains. No default is selected. Cost begins when removal code would need to guess which UI survives.
- **Worst case:** Keeping the overview confuses users into expecting remote multi-user access. Correct copy and remove the view if needed; do not broaden the trust boundary.

### Reasoning for JH-D01-B

- **Context:** **Technical; open, owner-reserved.** Chooses documentation handling for an approved removal scope, but the source reserves it to the owner; escalate loss of required public history as a scope concern. Source recommendation: original Question A; no answer is recorded by this backfill. A means archive, B delete; the original recommendation favors keeping history while stopping use. Product constraints: [root safety and privacy rules](../../../AGENTS.md). Original question wording and options (verbatim, after its label): What happens to the hosting instructions in `DEPLOY.md`? **A. Move them to `docs/archive/` with a "not supported" banner (recommended):** keeps history, stops anyone following them. **B. Delete them.** Original pre-question label: - [ ] **JH-D01-B** (only if A) ; all conditional gates remain pending.
- **Prerequisites:** JH-D01 = drop hosting and an owner answer on the instructions.

#### Option A: Archive instructions (Suggested)

- **What it is:** Move hosting instructions to docs/archive/ with a “not supported” banner. Keep a clear current local setup path.
- **Unlocks:** Historical context without presenting hosting as supported.
- **Blocks:** Complete removal of old hosting guidance from the working tree.
- **Risks:** Readers could still follow archived steps; use a visible warning and remove current links to unsafe instructions. Likelihood is Unknown — a link inventory and novice read-through of the warning would test mistaken support expectations.
- **Effort:** Unknown — documentation maintainer needs an inbound-link map and archive/banner diff to estimate work.
- **Money:** None — this choice adds no paid service; implementation/review labor is covered by the unmeasured Effort above.
- **Incompatible with:** B (Delete instructions) as simultaneous choices for JH-D01-B.
- **Needs first:** Identify current inbound deployment links and preserve local setup content.

#### Option B: Delete instructions

- **What it is:** Delete the hosting instructions rather than archive them. Preserve supported local instructions.
- **Unlocks:** A current tree without the obsolete hosting recipe.
- **Blocks:** Browsing that recipe within the current docs tree.
- **Risks:** An old link may break; use a local-only notice at a retained entry point where needed. Likelihood is Unknown — a local-link and fragment check after deletion would identify broken entry points.
- **Effort:** Unknown — documentation maintainer needs a local/hosted content split and deletion/link diff to estimate work.
- **Money:** None — this choice adds no paid service; implementation/review labor is covered by the unmeasured Effort above.
- **Incompatible with:** A (Archive instructions) as simultaneous choices for JH-D01-B.
- **Needs first:** Inventory links to DEPLOY Part 3 and distinguish hosting from local setup.

#### Trade-offs

| Axis | A (Suggested) | B |
|---|---|---|
| Current tree history | Archived with warning | Removed |
| Link handling | Redirect to warning/local setup | Replace or retire hosting links |

- **Downstream impact:**
  - **Changes:** DEPLOY.md Part 3, README hosting links and optional docs/archive content; no hosting commands are executed.
  - **Unblocks:** Documentation portion of the local-only change.
- **Cost of deferring:** Instructions remain in their current location while the parent decision is open. Cost begins when a reader mistakes the recipe for support; frequency is Unknown — support reports and link usage would settle it.
- **Worst case:** The archive is mistaken for endorsed hosting. Strengthen the unsupported banner, replace inbound links, or delete the recipe through a reviewed follow-up.

### Reasoning for JH-D01-C

- **Context:** **Technical; open, owner-reserved.** Chooses additional request validation within local scope; owner-reserved security gate. Escalate any remote-access allowance as a trust-boundary change. Source recommendation: original Question A; no answer is recorded by this backfill. Original A yes/B no are retained. The source’s “no effect on normal use” is unmeasured; verify alternate local hosts before making that claim. Product constraints: [root safety and privacy rules](../../../AGENTS.md). Original question wording and options (verbatim, after its label): Also reject requests whose Host isn't `localhost`/`127.0.0.1`? **A. Yes (recommended):** blocks DNS-rebinding reads; no effect on normal use. **B. No, Origin + CSRF are enough.** Original pre-question label: - [ ] **JH-D01-C** (only if A) ; all conditional gates remain pending.
- **Prerequisites:** JH-D01 = drop hosting and owner review of permitted local addresses.

#### Option A: Same computer only (Suggested)

- **What it is:** Reject requests whose Host is not localhost or 127.0.0.1, as the source proposes. Keep Origin and single-use CSRF protections too.
- **Unlocks:** Protection against DNS-rebinding reads as well as writes.
- **Blocks:** Use through other Host values without a reviewed exception.
- **Risks:** Alternate local addresses may stop working; test documented clients and revise an explicit local allow-list without allowing public hosting. Likelihood is Unknown — synthetic requests for all documented local addresses would identify compatibility failures.
- **Effort:** Unknown — security maintainer needs Host-validation fixtures and documented-client results to estimate work.
- **Money:** None — this choice adds no paid service; implementation/review labor is covered by the unmeasured Effort above.
- **Incompatible with:** B (Keep current layers) as simultaneous choices for JH-D01-C.
- **Needs first:** Design tests for allowed, missing and forged Host headers.

#### Option B: Keep current layers

- **What it is:** Do not add the Host restriction; retain Origin plus CSRF. The source describes those as enough, which is a choice rather than a newly verified safety claim.
- **Unlocks:** Existing address compatibility without a new Host check.
- **Blocks:** The proposed additional barrier to DNS-rebinding reads.
- **Risks:** Read exposure through rebinding may remain; investigate with a synthetic request test and add Host checks if confirmed. Likelihood is Unknown — a controlled DNS-rebinding read test would establish the remaining exposure.
- **Effort:** Unknown — security reviewer needs a controlled rebinding test and accepted-risk note to estimate review effort.
- **Money:** None — this choice adds no paid service; implementation/review labor is covered by the unmeasured Effort above.
- **Incompatible with:** A (Same computer only) as simultaneous choices for JH-D01-C.
- **Needs first:** Security review must record the accepted read-exposure limitation.

#### Trade-offs

| Axis | A (Suggested) | B |
|---|---|---|
| Read barrier | Additional Host restriction | Existing protections only |
| Address compatibility | localhost / 127.0.0.1 | Current addresses unchanged |

- **Downstream impact:**
  - **Changes:** admin/server.py request validation and related route tests only in a later change; privacy and confirmation rules remain.
  - **Unblocks:** The optional hardening slice within local-only removal.
- **Cost of deferring:** Existing local protections remain; this backfill cannot claim read protection. Cost begins with a rebinding exposure; likelihood is Unknown — a controlled exploit test and threat review would settle it.
- **Worst case:** The recommended restriction blocks a legitimate local client. Reproduce with synthetic requests and adjust only the documented loopback allow-list.
