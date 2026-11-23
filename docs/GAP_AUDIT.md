# Gap Audit

Implementation sequence, file-level changes, safety contracts, and release gates are defined in [the release and safety gap-closure proposal](proposals/PROPOSAL_RELEASE_AND_SAFETY_GAP_CLOSURE.md).

| ID | Priority | Gap | Direct injection location | Acceptance evidence |
|---|---|---|---|---|
| JH-001 | P0 local | No enforced CI. **2026-10-26: `.github/workflows/ci.yml` added.** It runs `compileall` and the offline suite on Python 3.10/3.11/3.12 for every PR and push to `main`, and fails if zero tests run (GAP-JH-03). Making it *block* merges is a repository setting: JH-D05 | `.github/workflows/ci.yml` | Unit suite runs on supported Python matrix; failure blocks merge (blocking half: JH-D05) |
| JH-002 | P0 local | **Closed for the test runner 2026-10-26.** `run_tests.py` forces `ACTIVE_PROFILE=example_profile` (placeholder identity), runs from a temp working directory, and removes its temp dirs on exit. Web-search tests now pass on a clean clone. Runtime `config.py` still creates `output/<profile>/` on import by design; moving that into an explicit init is proposal JH-WP1 work | `config.py`, `run_tests.py`, web/config tests | Synthetic fixture only; no personal identity/output side effects. Verified: default and `--api` runs leave the repo's `output/` untouched |
| JH-003 | P0 local | **Closed 2026-11-04 for the submit guard.** `submission_guard.py` `SubmissionGuard` is the only path to the Easy Apply Submit click. Each confirmation is a single-use token bound to the job (its URL) and a page fingerprint (URL plus submit label), expires after 120 s, can't be minted in dry-run, and is voided by navigation (`apply_to_job`), a newer confirmation or any refused attempt (fail-closed). Offline tests cover dry-run, single use, job/page scope, expiry, invalidation and a page change between confirming and clicking; each invariant was mutation-checked. Typed outcomes (GAP-JH-06) closed 2026-11-09 via JH-D07 (Auto Applied / User Applied) | `submission_guard.py`, `browser_apply.py`, safety tests | Dry-run has zero submit calls; each actual submit needs fresh confirmation |
| JH-004 | P0 local | **Closed 2026-10-23 (PR #5).** Hardcoded count removed from `TESTING.md`; `CONTRIBUTING.md` documents the runner | `TESTING.md`, `CONTRIBUTING.md` | Count generated or omitted; commands match runner |
| JH-005 | P0 local | Live and deterministic tests mixed. **2026-10-26: default `python run_tests.py` is offline-only** (matcher, storage, safety, config); live API/web/browser groups need `--api`, `--browser` or `--all`. Still open: no recorded provider fixtures, so live tests remain the only scraper coverage | `run_tests.py`, API/browser test modules | Offline default is deterministic; live suite is explicit and tolerant of provider drift |
| JH-006 | P0 hosted | No app authentication/authorization | `admin/server.py` app factory and all `/api/*` routes | Auth, role and object-ownership tests |
| JH-007 | P0 hosted | No CSRF protection. **Local first line added 2026-11-08:** every mutating admin request needs an allowed Origin/Referer (403 otherwise; covers all 15 write routes; BUG_TRACKER #13). **Token layer added 2026-11-09:** every write also needs a single-use, expiring token from `GET /api/csrf-token` (403 if missing, forged, replayed or expired), checked after the Origin check. **Still open for hosted mode:** per-user sessions and auth (JH-006, JH-D01) | Mutating admin routes | Cross-origin mutation is rejected; same-origin token flow passes |
| JH-008 | P0 hosted | Profile files execute Python | Profile loader and create/upload paths | Hosted profiles use declarative schema; no arbitrary code execution |
| JH-009 | P0 hosted | Upload validation incomplete | `/api/resumes/<profile>/upload` | Size, MIME, magic, filename, quota and ownership tests |
| JH-010 | P0 hosted | **Closed 2026-11-07.** CSV lost-update risk. **Atomic and locked writes closed 2026-11-04.** New `atomic_io.py`: temp file, fsync, `os.replace`, keeps file mode and user-added columns, no residue on failure, and a cross-process `<file>.lock` held for the whole read-modify-write. It's used by the admin job PATCH/bulk routes, run log, form config, profile writes, `local_sync` (`push_jobs` now rewrites atomically instead of appending), `run_scrape_browsers`, `ai_training`, `ats_fields`, `run_scrape` and `scraper`; no direct `open(..., 'w')` writes remain. Corrupt JSON fails visibly instead of being replaced. Tests: fault before replace, mode and columns, 8 concurrent writers × 25 updates, corrupt JSON, locked `mark_applied`, admin PATCH routes; each invariant mutation-checked. **Job IDs and conflicts closed 2026-11-07:** every job carries a stable `_id` (source plus canonical URL, ignoring case, trailing slash and `utm_*`) and a content `_rev`. The PATCH routes find the row by `_id` even after a scrape reorders the CSV, return 409 with the current row on a stale `_rev` (bulk is all-or-nothing), return 404 for a removed job, and still accept index-only requests. The admin UI sends both and reloads on 409 | storage helpers and job PATCH/scrape paths | Atomic write/locking or database transaction concurrency test |
| JH-011 | P0 hosted | Debug dev server was unconditional. **Debug half closed 2026-11-04:** `admin/server.py` `main()` runs with `debug=False` unless `--debug` or `ADMIN_DEBUG=1` is given, still loopback-only. Test `Admin debug off by default (JH-011)`; forcing `debug=True` fails it. **Still open:** a production WSGI command and proxy/security config, which belong to the hosted track (JH-D01) | `admin/server.py` entry point | Production WSGI command; debug false; proxy/security config documented |
| JH-012 | P1 | OpenTech handoff absent | new local adapter/runner, config example | Sanitized idempotent job/status ingestion with offline recovery |
| JH-013 | P1 | **Closed 2026-11-07.** `tests/admin_routes.py` (`run_tests.py --routes`, in the default offline run and CI) covers **all 33 admin routes** in a temp project tree (66 cases: success, validation, not-found, conflict), with the scrape subprocess stubbed and a ledger check that fails if any route goes uncovered. It found and fixed: profile-segment path traversal, a resume-route 500, `DELETE /api/profiles/__init__` deleting the package file (and the example template being writable), 500s on non-numeric settings/salaries, and form-config PUT accepting any JSON | `tests/admin_routes.py` | Success/auth/validation/not-found/conflict coverage per mutating route (auth only if hosted is retained, JH-D01) |
| JH-014 | P2 | **Closed 2026-10-26.** Matcher tests call `matcher.parse_salary`, `salary_in_range`, `match_title_to_role` and `match_jobs` against synthetic roles; the inline copies are deleted. Mutation check: breaking `k`-notation parsing in `matcher.py` fails the test | matcher test module | Tests exercise exported production functions |
| JH-015 | P1 | **Closed 2026-10-24.** Removed resume generator was still wired. `POST /api/ai-training/<profile>/generate-resume` now returns **410 Gone** with an upload-instead message and spawns nothing; `can_generate_resume` and the admin Generate button/handler are removed. `fpdf2` retention is split out as JH-D02 | `admin/server.py` `generate_ai_resume`, `admin/static/index.html` | Test `Generate-resume route is 410 (JH-015)` passes; it fails against the previous code (mutation check) |
| JH-016 | P1 | **Closed 2026-10-24.** The default profile name pointed nowhere. `config.py` now has no default: without `--profile` or `ACTIVE_PROFILE` it prints a clear error naming both, exits 1, and creates nothing. The test runner already records the exit as a failure instead of aborting (2026-10-23) | `config.py` `_get_profile_name`, `.env.example` | Test `No profile -> clear error (JH-016)` passes (temp cwd, no `output/`); it fails against the previous code (mutation check) |

## Open decisions (owner)

Open decisions use a plain question and short Suggested answer, with full same-document reasoning below. Answer with the ID and choice meaning. Resolved rows retain their historical wording unchanged; no answer is inferred from silence.

| ID | Decision | Options | Context | Question |
|---|---|---|---|---|
| JH-D01 | Disposition of deployed/hosted mode | See `PROPOSAL_RELEASE_AND_SAFETY_GAP_CLOSURE.md` §4 (it is also work package JH-WP6) | Open; not touched by local work. JH-006–011 depend on it Scope of the drop option: [`docs/design/proposals/2026-11-12-local-only-scope.md`](design/proposals/2026-11-12-local-only-scope.md) (sub-questions JH-D01-A/B/C) | **Question:** Should this tool drop shared online use and stay on one trusted person’s computer? **Suggested:** Local only |
| JH-D02 | Keep `fpdf2` in `requirements.txt`? | (a) drop it (nothing tracked imports it); (b) keep it for operators running a private local generator; (c) move it to an optional extras file | Split from JH-015 on 2026-10-24. Harmless either way; the choice depends on whether a generator will ship publicly | **Question:** Should the unused resume-making package be removed from the standard installation? **Suggested:** Remove package |
| JH-D03 | MIT copyright holder | (a) an organization's legal name; (b) the owner's legal name | **Answered 2026-10-27: the owner's legal name, "Alex Moody".** `LICENSE` and the README updated | **Question:** Whose name goes on the MIT copyright line? **Answered:** the owner's legal name |
| JH-D04 | Pre-rewrite data still public | (a) delete the branch and ask GitHub Support to purge cached refs; (b) leave it | **Resolved 2026-10-27.** The old repository was renamed `job-hunter-archive`, made private and archived. Its PR refs (which held the pre-rewrite data and could not be rewritten) are no longer public. This repository is a fresh single-commit re-creation. Full pre-scrub history is kept privately in `OpenTechnology14/Job-Hunter-Private` | **Question:** Delete the public data? **Answered:** archive the old repository privately and re-create the public one fresh |
| JH-D05 | Require CI before merging | (a) branch protection on `main` requiring `CI / offline-tests`; (b) keep CI advisory | CI was added 2026-10-26 (JH-001). An admin override would still be possible for an explicit owner instruction | **Question:** Should passing automated checks be required before changes are merged? **Suggested:** Require checks |
| JH-D06 | Personal email in commit metadata | (a) enable GitHub's "Keep my email addresses private"; (b) also rebuild affected commits | **Resolved 2026-11-07 (option a, no history rewrite).** After the owner granted the `user` scope, `PATCH /user/email/visibility` set primary-email visibility to **private**. Verified: a `gh` squash merge made right after the flip is authored by the noreply address, while merges just before it carried the personal one. `main` has been noreply-only since the re-creation. Still carrying the old address, and not rewritten: PR #3's commits (`0bd2ff8`, plus the `d958ba1` squash on `codex/agent-workflow-reference`) and `refs/pull/3/head`, which owners can't delete. The separate "Block command line pushes that expose my email" setting is web-only and still off; local commits use the noreply identity | **Question:** Turn on GitHub's email-privacy setting? **Answered:** yes, done 2026-11-07 |
| JH-D07 | Typed apply outcomes (GAP-JH-06) | Split "Done" by who clicked Submit | **Resolved 2026-11-09; labels locked by the owner:** **Auto Applied** (`auto_applied`: Job Hunter's guarded click) and **User Applied** (`user_applied`: Job Hunter prefilled, you clicked Submit and answered y). "Reviewed" is retired. Historical Done → Auto Applied, with a one-time needs-review tag on non-Easy-Apply rows (`python apply_status.py --profile <p> --migrate`). Design: [`docs/design/proposals/2026-11-09-auto-vs-user-applied.md`](design/proposals/2026-11-09-auto-vs-user-applied.md) | **Question:** How should Done be split? **Answered:** Auto Applied / User Applied |
| JH-D08 | PR #1 (`codex/agent-workflow-reference`) carries the personal email | (a) squash-merge only; (b) rebuild its commits first; (c) merge as-is | **Resolved 2026-11-08: owner chose A, squash only.** PR #1's head `d958ba1` keeps the old address in its own metadata, but a squash merge writes a new noreply-authored commit, so it never reaches `main`. Generalized as a standing rule in AGENTS.md, CONTRIBUTING.md and AGENT_STEERING_AND_STANDUPS.md: any PR with pre-2026-11-07 commits is squash-merged. PR #1 still has to resolve its conflicts with `main` (branch owner) | **Question:** Land PR #1 as a squash merge instead of rebuilding it? **Answered:** A, squash only |

There are no other `JH-WP*` decisions. JH-WP6 *is* JH-D01; JH-WP0–WP5 are implementation work with no open owner choice.

Local release work must not accidentally imply hosted readiness. Track and label the two release profiles separately.

## Decision reasoning — documentation backfill, 2026-11-22

**Proposed:** The choices below remain open. Source recommendations are preserved; classification supplies no implementation or release approval. Historical option mappings are retained explicitly where they conflict.

### Reasoning for JH-D01

- **Context:** **Strategic; open, owner-reserved.** Chooses the supported release scope and security investment, across the safety proposal, local-only scope, optional integration and admin-future proposal. Source recommendation: original Question A; no answer is recorded by this backfill. This table has no recommendation column: the new Suggested is the author’s presentation of that same source recommendation, not an owner answer. The release proposal broadly says removing hosting closes JH-006 through JH-011; the newer local-only scope limits not-applicable closure to hosted parts (JH-006/008/009/011) and retains JH-007 local protections. Both dated statements remain; no gap is closed by this backfill. Code reading at the task base shows DEPLOYED_MODE still exists and main binds loopback; the proposed refusal to start is not implemented. JH-WP6 is this same gate, not another decision. Product constraints: [root safety and privacy rules](../AGENTS.md). Original question wording and options (verbatim, after its label): Should Job Hunter drop its multi-user "deployed" mode and stay a local, single-user tool? **A. Yes, drop it (recommended):** fastest safe release; no hosted option. **B. No, keep it:** auth, CSRF and tenant isolation must be built first
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

### Reasoning for JH-D02

- **Context:** **Technical; open, owner-reserved.** Settles dependency packaging within the current user-supplied-resume scope; owner-reserved despite technical classification. Escalate any proposal to ship a public generator as strategic scope. Source recommendation: original Question A; no answer is recorded by this backfill. This table has no recommendation column: the new Suggested is the author’s presentation of that same source recommendation, not an owner answer. Original Options (a)/(b)/(c) mean remove/keep/optional extras; Question A/B mean remove/keep. The third choice was absent from the old question and is retained here as C with original (c). Product constraints: [root safety and privacy rules](../AGENTS.md). Original question wording and options (verbatim, after its label): Remove the unused `fpdf2` dependency? **A. Yes, remove it (recommended):** nothing in the repo uses it. **B. No, keep it:** only useful if you run a private resume generator from this checkout
- **Prerequisites:** Owner confirmation of whether private generator support belongs in the standard installation.

#### Option A: Remove package (Suggested)

- **What it is:** Remove fpdf2 from the default requirements. No tracked Python module currently imports it.
- **Unlocks:** A default install without this unused package.
- **Blocks:** Private generators relying on its automatic installation.
- **Risks:** A private generator could stop working; an explicit separate installation or optional file can restore it. Likelihood is Unknown — a private-generator dependency inventory would identify affected installations.
- **Effort:** Unknown — maintainer needs a requirements diff and clean-install check to estimate removal time.
- **Money:** None — this choice adds no paid service; implementation/review labor is covered by the unmeasured Effort above.
- **Incompatible with:** B (Keep package); C (Optional extras) as simultaneous choices for JH-D02.
- **Needs first:** Confirm private-generator users have a documented installation path.

#### Option B: Keep package

- **What it is:** Keep fpdf2 in the standard requirements for operators running a private local generator. This does not ship a generator publicly.
- **Unlocks:** Existing private-generator installations keep their dependency.
- **Blocks:** Removing the unused default dependency.
- **Risks:** Users may assume a generator is included; clarify the absent public generator and reconsider packaging. Likelihood is Unknown — a setup walkthrough would show whether users expect an included generator.
- **Effort:** Unknown — maintainer needs a dependency/support-note review to estimate ongoing upkeep.
- **Money:** None — this choice adds no paid service; implementation/review labor is covered by the unmeasured Effort above.
- **Incompatible with:** A (Remove package); C (Optional extras) as simultaneous choices for JH-D02.
- **Needs first:** Retain the upload workflow and absent-generator statement.

#### Option C: Optional extras

- **What it is:** Move fpdf2 to an optional extras file, as original Options (c) states. Operators needing a private generator install that file explicitly.
- **Unlocks:** Separate generator support without a default dependency.
- **Blocks:** One-command default installation for that private use.
- **Risks:** Users may miss the extra install step; add explicit private-generator setup instructions without publishing private source. Likelihood is Unknown — a clean optional-file installation walkthrough would reveal missed steps.
- **Effort:** Unknown — maintainer needs an optional-file setup prototype and install check to estimate duration.
- **Money:** None — this choice adds no paid service; implementation/review labor is covered by the unmeasured Effort above.
- **Incompatible with:** A (Remove package); B (Keep package) as simultaneous choices for JH-D02.
- **Needs first:** Define and document the optional requirements file in a later approved packaging change.

#### Trade-offs

| Axis | A (Suggested) | B | C |
|---|---|---|---|
| Default install | No fpdf2 | fpdf2 included | No fpdf2 |
| Private generator setup | Separate manual install | Already installed | Explicit optional file |

- **Downstream impact:**
  - **Changes:** requirements.txt and generator/setup notes would change for A/C; B keeps the dependency and may clarify docs. JH-015 remains closed; no generator or runtime change is authorized.
  - **Unblocks:** A packaging follow-up after an answer; no public-generator release.
- **Cost of deferring:** The unused dependency stays installed. Local upload/apply work continues; no implied generator approval. Unknown — a dependency inventory and install-size measurement would settle the actual maintenance cost.
- **Worst case:** Removal breaks a private generator’s setup. Restore an explicit installation instruction or optional dependency without importing private generator code.

### Reasoning for JH-D05

- **Context:** **Strategic; open, owner-reserved.** Chooses release-risk acceptance and repository governance; technical configuration follows that owner choice. Source recommendation: original Question A; no answer is recorded by this backfill. This table has no recommendation column: the new Suggested is the author’s presentation of that same source recommendation, not an owner answer. Original (a)/(b) and Question A/B agree. The source recommends requiring checks. CI exists in .github/workflows/ci.yml; this backfill neither queries nor changes branch protection. Product constraints: [root safety and privacy rules](../AGENTS.md). Original question wording and options (verbatim, after its label): Make the new CI check required before anything merges into `main`? **A. Yes (recommended):** broken or unsafe changes can't land unnoticed; merges wait a few minutes. **B. No, keep it advisory**
- **Prerequisites:** An owner answer and confirmation of the repository’s available branch-rule permissions.

#### Option A: Require checks (Suggested)

- **What it is:** Require CI / offline-tests on main through branch protection. Preserve the documented explicit per-PR owner override policy.
- **Unlocks:** A failing required check blocks ordinary merges.
- **Blocks:** Routine merges while required checks are failing or pending.
- **Risks:** An unavailable check could block a safe change; use the explicit named-PR owner procedure and record outstanding evidence. Likelihood is Unknown — recent workflow failures and durations would establish outage blockage.
- **Effort:** Unknown — repository owner needs exact branch-rule permissions/check names and a configuration review to estimate setup time.
- **Money:** None — this choice adds no paid service; implementation/review labor is covered by the unmeasured Effort above.
- **Incompatible with:** B (Advisory checks) as simultaneous choices for JH-D05.
- **Needs first:** Verify the Python-matrix check names and branch-rule capabilities.

#### Option B: Advisory checks

- **What it is:** Keep the offline workflow advisory. Maintainers inspect results before acting under existing merge authority.
- **Unlocks:** Maintainer judgment without a required-check wait.
- **Blocks:** Automatic blocking of failing ordinary merges.
- **Risks:** A failed check may be missed and unsafe work land; inspect every result and revert an offending change without weakening safety. Likelihood is Unknown — a PR/check audit would establish how often failing results are overlooked.
- **Effort:** Unknown — maintainer needs recent PR volume and review timings to estimate ongoing manual cost.
- **Money:** None — this choice adds no paid service; implementation/review labor is covered by the unmeasured Effort above.
- **Incompatible with:** A (Require checks) as simultaneous choices for JH-D05.
- **Needs first:** A maintainer must own review of every relevant result.

#### Trade-offs

| Axis | A (Suggested) | B |
|---|---|---|
| Ordinary failing check | Blocks merge | Does not block automatically |
| Availability dependency | Required check must complete | Human review of result |

- **Downstream impact:**
  - **Changes:** A changes repository branch rules; B retains advisory settings. Neither changes test code or grants merge authority.
  - **Unblocks:** A repository-setting task after owner approval; local docs work does not depend on that setting.
- **Cost of deferring:** Advisory behavior continues; risk persists whenever a PR is merged without inspecting results. Source says merges wait a few minutes; actual duration is Unknown — recent workflow timings would settle it.
- **Worst case:** Required checks become unavailable and block urgent work. Confirm the exact outage, retain failed/unrun evidence, and use only a named-PR owner override.
