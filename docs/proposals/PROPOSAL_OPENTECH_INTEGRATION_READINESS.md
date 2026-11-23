# Proposal: OpenTech Integration and Release Readiness

**Status:** Draft
**Date:** 2026-07-12
**Release profile:** Local single-user first; hosted mode excluded
**Evidence:** Job-Hunter state verified; integration proposed

## 1. Executive summary

Add a local Job-Hunter runner that can synchronize sanitized job workflow state with an OpenTech Job Hunter project template. OpenTech becomes the planning/review UI; Job-Hunter remains the local executor for scraping, matching, resume selection, browser navigation, and supervised form filling. Submissions always remain under direct user control.

## 2. Verified current state

- Job-Hunter has working local source, matching, storage, browser, and configuration tests, but no enforced CI.
- It stores sensitive profiles, resumes, form answers, history, and credentials locally and ignores them in Git.
- The Flask admin surface has 33 routes and no in-app auth/CSRF; this proposal does not expose it publicly.
- OpenTech has a Job Hunter template and queue-ingest concept, while Job-Hunter has no current adapter.
- Existing template/proposal material expects a local runner for scraping/apply capabilities that the web UI should not perform.

## 3. Goals and non-goals

### Goals

- Make OpenTech the optional queue/status/review surface for local Job-Hunter runs.
- Preserve local storage and explicit submission confirmation.
- Add deterministic CI and safety tests needed for a public local release.
- Make synchronization idempotent, recoverable, and private by construction.

### Non-goals

- Hosting the Flask admin server as a public multi-user service.
- Uploading resumes, form answers, credentials, browser state, or full profile data to OpenTech.
- Letting OpenTech or any unattended task submit an application.
- Replacing Job-Hunter's source adapters with remote browser automation.

## 4. User paths

1. User imports/creates the OpenTech Job Hunter project and copies a project/queue identifier.
2. Local setup validates Job-Hunter configuration and optionally tests the OpenTech endpoint with a synthetic event.
3. A scrape/match run creates or updates sanitized queue items.
4. User selects an item for local preparation. The runner resolves private profile/resume/form data locally.
5. Browser assistance navigates/fills. Immediately before any submit action, the local UI asks for a fresh confirmation.
6. Completion/failure status is synchronized. During an outage, a bounded local outbox retries idempotently.
7. Disconnecting clears unsent events and leaves local job/history data intact.

## 5. Architecture and data flow

```text
OpenTech Job Hunter template
     ^ sanitized status/tasks
     | HTTPS, opt-in, idempotent
Local Job-Hunter adapter/outbox
     |
scrapers -> matcher -> local CSV/profile/resume -> supervised browser
```

Allowed outbound fields: stable opaque job ID, company, title, public job URL, public source, coarse location, workflow status, timestamps, safe error reason, and aggregate match band if enabled. Forbidden: name/contact details, resume bytes/path, form answers, credentials/tokens, cookies/session state, demographic answers, salary preferences unless explicitly selected, local filesystem paths, and browser screenshots.

## 6. Direct injection map

| Location | Symbol/surface | Proposed change | Example | Verification |
|---|---|---|---|---|
| `integrations/opentech/client.py` (new) | `OpenTechClient.ingest()` | Typed timeout/retry client with idempotency header | request below | Fake-server contract tests |
| `integrations/opentech/sanitize.py` (new) | `to_queue_item()` | Field allow-list and stable opaque ID | forbidden-field rejection | Property/privacy tests |
| `integrations/opentech/outbox.py` (new) | local outbox | Atomic bounded retry queue | max age/count config | Crash/replay/outage tests |
| `config.example.py` or `.env.example` | integration settings | Disabled default; endpoint/project/queue and secret reference | `OPENTECH_ENABLED=false` | Config validation |
| scrape orchestration entry point | post-persist hook | Enqueue sanitized upserts after local save | one batch/event | Duplicate and partial-failure tests |
| `browser_apply.py` | completion/failure hook | Emit status only after local terminal state | no private form data | Safety/redaction tests |
| `run_tests.py` | `--opentech` group | Add offline client/sanitizer/outbox suite | required in CI | Collection/count test |
| `.github/workflows/ci.yml` (new) | offline test job | Synthetic profile/temp filesystem; live smoke separate | Python matrix | Deliberate failure gate |
| OpenTech template | Job Hunter template JSON | Remove personal examples; add runner setup/status/review fields | generic fixture | Import/schema test |

## 7. Contracts and examples

### OpenTech ingestion request

```http
POST /api/queues/{queueId}/ingest
Authorization: Bearer <token>
Idempotency-Key: jh:job_7f2a:status:matched:v3
Content-Type: application/json
```

```json
{
  "source": "job-hunter-local",
  "items": [
    {
      "external_id": "job_7f2a",
      "title": "Software Engineer",
      "company": "Example Company",
      "source": "lever",
      "public_url": "https://jobs.example/job/123",
      "location": "Remote",
      "status": "matched",
      "match_band": "strong",
      "updated_at": "2026-07-12T18:00:00Z"
    }
  ]
}
```

### Local runner status

```json
{
  "runner_version": "0.x",
  "connected": true,
  "outbox_depth": 0,
  "last_sync_at": "2026-07-12T18:00:02Z",
  "supervision": "required_for_submit"
}
```

Stable errors: `invalid_config`, `unauthorized`, `rate_limited`, `endpoint_unavailable`, `payload_rejected`, `privacy_field_rejected`, `outbox_full`. Logs must not include authorization values or rejected private field values.

## 8. Security, privacy, and supervision

- Integration is disabled by default and limited to an allow-listed HTTPS origin outside local test mode.
- Token storage uses an environment/OS secret reference and is never returned by `/api/setup`.
- The outbox is permission-restricted and stores only already-sanitized payloads.
- Dry-run cannot call any submit primitive. Confirmation is scoped to one job, one page state, and a short expiry; navigation invalidates it.
- OpenTech “Apply” means “open a supervised local preparation task,” never remote submission.

## 9. Test and pressure matrix

| ID | Scenario | Type | Expected result | Gate |
|---|---|---|---|---|
| OTJ-01 | Integration disabled | Deterministic | Zero outbound requests/outbox records | P0 |
| OTJ-02 | Synthetic upsert | Contract | One valid generic queue item | P0 |
| OTJ-03 | Private fields injected | Privacy | Rejected/dropped; values absent from logs/outbox | P0 |
| OTJ-04 | Same event replayed | Contract | One logical update | P0 |
| OTJ-05 | Endpoint offline/recovery | Pressure | Bounded retry and ordered recovery | P1 |
| OTJ-06 | Crash during outbox write | Recovery | Valid old or new record; no corrupt state | P0 |
| OTJ-07 | Dry-run on every apply adapter | Safety | Zero submit calls | P0 |
| OTJ-08 | Confirm first of two jobs | Safety | Second job cannot reuse confirmation | P0 |
| OTJ-09 | Real profile absent in CI | Isolation | Synthetic tests pass with no personal output | P0 |
| OTJ-10 | Provider API changes | Live smoke | Visible provider failure; integration/local data preserved | P1 |

## 10. Delivery plan

1. **Release truth:** fix test isolation/docs and add offline CI plus submission invariants.
2. **Sanitizer/client:** implement typed allow-list and fake-server contract tests.
3. **Atomic outbox:** bounded queue, retry/backoff, crash recovery, operator status.
4. **Workflow hooks:** sync scrape/match/preparation/terminal status behind a disabled-default flag.
5. **OpenTech template:** genericize examples, document runner setup, add readiness/status/review tasks.
6. **Alpha:** opt-in local users, metrics limited to local logs, rollback rehearsal.

## 11. Rollout and rollback

Start with synthetic endpoint tests, then a private OpenTech project. Roll back by setting `OPENTECH_ENABLED=false`, deleting the sanitized outbox, and revoking the token. No local job/profile/resume data is removed and scraping/matching/browser assistance remains available.

## 12. Risks and unresolved decisions

IDs were added 2026-10-26 so answers can be recorded. None of these blocks current local work: the integration is sequenced after JH-WP1–WP4.

| ID | Item | Decision owner | Default | Question |
|---|---|---|---|---|
| JH-OT-D01 | Exact OpenTech ingest schema/version compatibility | OpenTech API owner | Reject mismatches — source recommendation | **Question:** Should the connection reject updates written for a different data format version? **Suggested:** Reject mismatches |
| JH-OT-D02 | Whether coarse location and match band are enabled by default | Privacy/product owner | Off until enabled — source recommendation | **Question:** Should approximate job locations and match ratings be shared automatically? **Suggested:** Off until enabled |
| JH-OT-D03 | Outbox maximum count/age | Maintainer | Example limits — source recommendation | **Question:** Should pending updates expire after seven days and stop at one thousand items? **Suggested:** Example limits |
| JH-OT-D04 | Token storage mechanism by OS | Security/desktop owner | Protected store — source recommendation | **Question:** Should the connection’s access secret be kept in the computer’s protected password store? **Suggested:** Protected store |
| JH-OT-D05 | Long-term CSV vs SQLite persistence | Job-Hunter maintainer | Keep spreadsheets — source recommendation | **Question:** Should jobs stay in spreadsheet files instead of moving to a local database? **Suggested:** Keep spreadsheets |

## 13. Existing-document updates

Update the README, setup checklist, testing guide, security policy, health check, app playbook, source list, OpenTech template README, and API documentation as each phase ships. Do not document the integration as available before the adapter and template import tests pass.

## 14. Next concrete step (scoped 2026-10-23, not started)

Delivery step 1 ("release truth") is owned by [`PROPOSAL_RELEASE_AND_SAFETY_GAP_CLOSURE.md`](PROPOSAL_RELEASE_AND_SAFETY_GAP_CLOSURE.md): JH-WP5 runs only after WP1–WP4. The first OpenTech-specific step that doesn't wait on code is a **sanitizer contract fixture**. This is a deterministic table of every candidate job/status field, each marked allow or deny, with a forbidden-field test (OTJ-03) written against it before `integrations/opentech/sanitize.py` exists. It's blocked by sequencing, not by a decision, except for one open privacy-owner item in §12: whether coarse location and match band are allowed by default. The fixture should mark those two as **Blocked** rather than guess.

## Decision reasoning — documentation backfill, 2026-11-22

**Proposed:** The choices below remain open. Source recommendations are preserved; classification supplies no implementation or release approval. Historical option mappings are retained explicitly where they conflict.

### Reasoning for JH-OT-D01

- **Context:** **Technical; open, owner-reserved.** Chooses interoperability mechanics for the optional integration; expressly reserved to the OpenTech API owner. Escalate a changed consumer contract or rollout commitment. Source recommendation: original Question A; no answer is recorded by this backfill. Original Question A rejects mismatches (recommended); B best-effort. Source table had no recommendation column; Default is added to preserve that explicit source recommendation. Product constraints: [root safety and privacy rules](../../AGENTS.md). Original question wording and options (verbatim, after its label): Pin Job Hunter to one versioned OpenTech ingest schema and reject mismatches? **A. Yes (recommended):** mismatches fail visibly instead of corrupting the queue. **B. No, best-effort**
- **Prerequisites:** JH-WP1–WP4 evidence and a compatible API-owner contract; integration remains opt-in and proposed.

#### Option A: Reject mismatches (Suggested)

- **What it is:** Pin one versioned OpenTech ingest schema and reject incompatible updates. Report a visible mismatch rather than silently guessing.
- **Unlocks:** Explicit contract failure and testable compatibility.
- **Blocks:** Best-effort acceptance across unknown versions.
- **Risks:** A server upgrade may stop synchronization; retain sanitized events within approved bounds and update the contract after review. Likelihood is Unknown — upgrade/mismatch fixtures against the API-owner version contract would show rejected valid updates.
- **Effort:** Unknown — API owner and maintainer need the version contract and mismatch fixtures to size client work.
- **Money:** None — rejecting a version mismatch is local validation and requires no purchased service. Any endpoint subscription is a separate integration cost shared by both choices; implementation labor belongs in Effort.
- **Incompatible with:** B (Best effort) as simultaneous choices for JH-OT-D01.
- **Needs first:** API owner provides the supported version and mismatch response fixture.

#### Option B: Best effort

- **What it is:** Attempt ingestion without a strict version mismatch rejection. Keep field allow-lists and submission safeguards regardless.
- **Unlocks:** Potential compatibility across versions without a coordinated version pin.
- **Blocks:** A reliable early refusal of incompatible formats.
- **Risks:** A changed field could corrupt queue meaning; detect through contract fixtures, stop sync and repair sanitized state. Likelihood is Unknown — version-drift fixtures would show whether guessed fields alter queue meaning.
- **Effort:** Unknown — API owner and maintainer need supported drift cases and compatibility fixtures to size client work.
- **Money:** None — best-effort format handling is client logic with no purchased compatibility service specified. Any endpoint subscription is shared with strict validation; the extra compatibility work belongs in Effort.
- **Incompatible with:** A (Reject mismatches) as simultaneous choices for JH-OT-D01.
- **Needs first:** Define which format differences are safe and prove forbidden fields stay excluded.

#### Trade-offs

| Axis | A (Suggested) | B |
|---|---|---|
| Mismatch behavior | Visible refusal | Attempt compatible interpretation |
| Upgrade coordination | Version agreement first | Broader compatibility tests |

- **Downstream impact:**
  - **Changes:** Proposed integrations/opentech/client.py, sanitizer fixtures and API contract; API-owner coordination is limited to what this public proposal already describes.
  - **Unblocks:** Contract fixtures and later client implementation after sequencing and authority are satisfied.
- **Cost of deferring:** Client compatibility remains unsettled; current local scrape/apply continues. No best-effort default is authorized. Cost begins when either endpoint is implemented against an assumed version.
- **Worst case:** Strict pinning interrupts valid sync after an upgrade. Disable integration, preserve local jobs, agree a new fixture and resume sanitized replay.

### Reasoning for JH-OT-D02

- **Context:** **Strategic; open, owner-reserved.** Chooses the default privacy boundary and product behavior, across optional integration and local-first scope; reserved to privacy/product owner. Source recommendation: original Question A; no answer is recorded by this backfill. A off (recommended), B on. Public §5 lists coarse location among candidate fields while §14 explicitly blocks the default choice; neither is permission to send it before this answer. Product constraints: [root safety and privacy rules](../../AGENTS.md). Original question wording and options (verbatim, after its label): Send coarse location and match band to OpenTech by default? **A. No, off until you enable them (recommended):** matches the local-first privacy rule. **B. Yes, on by default**
- **Prerequisites:** Privacy/product owner approves exact fields and default behavior; integration’s existing opt-in and sequencing requirements still apply.

#### Option A: Off until enabled (Suggested)

- **What it is:** Leave coarse location and match band off until explicitly enabled. No precise personal location or salary preference becomes permitted.
- **Unlocks:** A smaller outbound default matching local-first privacy.
- **Blocks:** Automatic use of those fields in the remote queue.
- **Risks:** The remote view may lack useful context; offer explicit field-level enablement after the owner reviews a fixture. Likelihood is Unknown — a remote-review walkthrough without those fields would establish lost usefulness.
- **Effort:** Unknown — privacy owner and maintainer need allow-list fixtures and setup-toggle copy to size work.
- **Money:** None — omitting these fields requires no purchase or additional remote storage for them. Any baseline connection charge is separate; implementing field controls belongs in Effort.
- **Incompatible with:** B (On by default) as simultaneous choices for JH-OT-D02.
- **Needs first:** Mark both fields Blocked in the sanitizer fixture until the answer is recorded.

#### Option B: On by default

- **What it is:** Include the two proposed fields by default when the optional connection is enabled. Keep all forbidden personal fields excluded.
- **Unlocks:** Queue location and match context without an extra field toggle.
- **Blocks:** The minimum-data default for these fields.
- **Risks:** Unexpected sharing could violate user expectations; disable fields and clear affected remote records where supported, acknowledging copies may remain. Likelihood is Unknown — a consent review and synthetic outbound capture would establish unexpected exposure.
- **Effort:** Unknown — privacy owner and maintainer need consent/default/deletion fixtures to size work.
- **Money:** Unknown — any incremental transfer or remote-storage charge for these two fields needs their serialized sizes, event rate, retention period, and the actual endpoint’s quotas and billing rules. Baseline connection charges are common to both choices; consent and sanitizer work belong in Effort.
- **Incompatible with:** A (Off until enabled) as simultaneous choices for JH-OT-D02.
- **Needs first:** Document exact coarse-location/match-band definitions, consent, and deletion behavior.

#### Trade-offs

| Axis | A (Suggested) | B |
|---|---|---|
| Default data | Two fields excluded | Two fields included |
| User action | Enable fields explicitly | Enable connection only |

- **Downstream impact:**
  - **Changes:** Sanitizer allow-list fixture, setup defaults and remote queue display; local-only use and submit confirmation do not change.
  - **Unblocks:** Final classification of these two fixture fields, then privacy tests under the integration proposal.
- **Cost of deferring:** The fixture leaves these fields Blocked. Other authorized local work continues; no outbound field is enabled by silence. Cost starts when a consumer requires those fields.
- **Worst case:** Off defaults make queue review less useful. Let users deliberately enable the approved fields; do not broaden the allow-list automatically.

### Reasoning for JH-OT-D03

- **Context:** **Technical; open, owner-reserved.** Sets bounded-outage delivery mechanics for approved sanitized sync; maintainer-reserved. Escalate retention, data-loss acceptance or spend changes. Source recommendation: original Question A; no answer is recorded by this backfill. Original A starts with the examples (recommended); B chooses other limits. These numbers are explicitly unmeasured in the source. Product constraints: [root safety and privacy rules](../../AGENTS.md). Original question wording and options (verbatim, after its label): Cap the offline outbox by count and age, with example defaults of 1,000 items / 7 days (placeholders, not measured)? **A. Yes, start there (recommended).** **B. Choose other limits**
- **Prerequisites:** Maintainer approves the retention/drop policy, integration prerequisites, and synthetic outage/replay evidence.

#### Option A: Example limits (Suggested)

- **What it is:** Start with a cap of 1,000 outbox items and 7 days. These are the source’s placeholders, not measured capacity or retention guarantees.
- **Unlocks:** Concrete initial bounds for outage tests.
- **Blocks:** Indefinite retry storage and a different initial limit.
- **Risks:** Updates may expire before recovery or capacity may be too large; expose drops and tune against outage fixtures before release. Likelihood is Unknown — event-volume and long-outage fixtures with 1,000 items/7 days would quantify losses and disk use.
- **Effort:** Unknown — maintainer needs bounded-outbox eviction/replay fixtures at the example limits to estimate work.
- **Money:** Unknown — whether these example limits require extra local storage needs measured sanitized-event sizes at the 1,000-item cap, event volume over seven days, available disk capacity and the price of any additional storage actually required. Optional-connection charges are common to either limit policy; outbox implementation belongs in Effort.
- **Incompatible with:** B (Other limits) as simultaneous choices for JH-OT-D03.
- **Needs first:** Specify eviction/order/reporting and run OTJ-05/06 with the proposed caps.

#### Option B: Other limits

- **What it is:** Choose different count and age caps. Keep the outbox bounded, atomic and sanitized.
- **Unlocks:** Limits based on observed traffic and recovery requirements.
- **Blocks:** Using the example caps as the initial policy.
- **Risks:** Unmeasured replacement values may still lose updates or grow too far; compare synthetic outage results and revise. Likelihood is Unknown — the same fixtures with proposed replacement caps would compare losses and storage.
- **Effort:** Unknown — maintainer needs event-volume measurements and a cap comparison to estimate sizing/review work.
- **Money:** Unknown — incremental local storage expenditure needs the proposed replacement count/age caps, measured event sizes and arrival rate, available disk capacity and the price of any additional storage actually required. Optional-connection charges are independent of choosing these local bounds; sizing and eviction work belong in Effort.
- **Incompatible with:** A (Example limits) as simultaneous choices for JH-OT-D03.
- **Needs first:** Collect expected event volume, tolerable outage age and disk usage before proposing values.

#### Trade-offs

| Axis | A (Suggested) | B |
|---|---|---|
| Initial cap | 1,000 items / 7 days, placeholders | Values not yet chosen |
| Sizing evidence | Validate example limits | Gather evidence then choose |

- **Downstream impact:**
  - **Changes:** Proposed outbox limits, full/expired error behavior and tests; no outbox exists here to reconfigure.
  - **Unblocks:** Bounded-outbox design after a maintainer answer; count/age choices do not authorize enabling sync.
- **Cost of deferring:** Outbox sizing remains blocked; local operations can continue disconnected. No placeholder becomes a runtime default. Cost starts when events would queue during an outage.
- **Worst case:** Example caps discard useful updates during a long outage. Surface expired/full counts, rebuild sanitized current state after reconnect and revise approved limits.

### Reasoning for JH-OT-D04

- **Context:** **Technical; open, owner-reserved.** Selects secret storage within the proposed integration; security/desktop owner reserves the answer. Escalate changed credential exposure or platform support. Source recommendation: original Question A; no answer is recorded by this backfill. A keychain (recommended), B git-ignored file. §8 proposes an environment/OS reference; this remains a constraint to reconcile with any file choice, not a reason to erase B. Product constraints: [root safety and privacy rules](../../AGENTS.md). Original question wording and options (verbatim, after its label): Store the OpenTech token in the operating-system keychain? **A. Yes (recommended):** the token never sits in a plain file. **B. No, a git-ignored file is acceptable**
- **Prerequisites:** Security/desktop owner approves storage, supported operating systems and a synthetic secret-handling test plan; no credential is requested here.

#### Option A: Protected store (Suggested)

- **What it is:** Store the OpenTech token in the operating-system keychain. Keep only a secret reference in configuration.
- **Unlocks:** Avoiding token plaintext in project files.
- **Blocks:** A plain-file-only setup across systems.
- **Risks:** A locked or unavailable keychain may prevent sync; fail closed and preserve local operation while the user unlocks it. Likelihood is Unknown — supported-OS tests with locked/missing keychains would establish setup failures.
- **Effort:** Unknown — desktop maintainer needs supported-OS keychain prototypes and failure fixtures to size work.
- **Money:** None for the operating-system password store itself, where already present. Unknown — the chosen keychain adapter’s license and supported-platform requirements would establish any added dependency cost; optional-connection charges are separate.
- **Incompatible with:** B (Ignored file) as simultaneous choices for JH-OT-D04.
- **Needs first:** Verify supported-system keychain APIs and unavailable-store behavior with synthetic tokens.

#### Option B: Ignored file

- **What it is:** Store the token in a git-ignored file, as the source alternative allows. Restrict access and keep values out of logs and outbound error payloads.
- **Unlocks:** A file-based setup where keychain access is unavailable.
- **Blocks:** The source’s promise that no token sits in a plain file.
- **Risks:** A copied file or backup may expose the token; revoke it, remove copies where possible and move to protected storage. Likelihood is Unknown — permission, backup and redaction tests with a synthetic token would establish file exposure paths.
- **Effort:** Unknown — security maintainer needs file-permission, backup, rotation and redaction fixtures to size work.
- **Money:** None — a permission-restricted file uses the existing local filesystem, with no purchased secret-storage service or new dependency specified. File-security and rotation work belong in Effort; optional-connection charges are separate.
- **Incompatible with:** A (Protected store) as simultaneous choices for JH-OT-D04.
- **Needs first:** Approve path permissions, backup handling, rotation and redaction behavior before implementation.

#### Trade-offs

| Axis | A (Suggested) | B |
|---|---|---|
| Plaintext file | Avoided | Present locally |
| Platform dependency | Keychain availability | Filesystem permissions/backup policy |

- **Downstream impact:**
  - **Changes:** Integration setup, secret reference resolution and platform tests; no real token or secret store is touched.
  - **Unblocks:** A credential-storage design review and later implementation after integration prerequisites.
- **Cost of deferring:** Storage stays undecided and integration stays unavailable. Other local work proceeds; no fallback file is silently created. Cost begins when a supported system needs connection setup.
- **Worst case:** Protected storage fails on a supported system. Disable sync, diagnose with synthetic tokens and approve a platform-specific recovery without exposing credentials.

### Reasoning for JH-OT-D05

- **Context:** **Technical; open, owner-reserved.** Selects persistence implementation while retaining local-first behavior; maintainer-reserved. Escalate loss of spreadsheet editing or a database-server requirement as strategic scope. Source recommendation: original Question A; no answer is recorded by this backfill. A CSV plus atomic writes (recommended), B SQLite. The old recommendation says JH-010 still needs atomic writes; GAP_AUDIT now records them closed, and local_sync imports atomic_io. The source’s dated recommendation is retained, not a claim that those writes are missing. Product constraints: [root safety and privacy rules](../../AGENTS.md). Original question wording and options (verbatim, after its label): Keep CSV as the main job store? **A. Yes, and add atomic writes (recommended):** keeps the open-in-a-spreadsheet workflow; JH-010 needs atomic writes anyway. **B. Move to SQLite**
- **Prerequisites:** Maintainer answer, existing atomic/revision evidence and a migration/rollback contract for any store change.

#### Option A: Keep spreadsheets (Suggested)

- **What it is:** Keep CSV as the main job store and retain atomic writes. This is the original recommended choice.
- **Unlocks:** Opening and editing jobs in a spreadsheet with existing local tools.
- **Blocks:** Replacing CSV as the main source of truth.
- **Risks:** Concurrent edits still require locking and revisions; keep existing guards and reproduce conflicts with synthetic data. Likelihood is Unknown — a concurrent synthetic scrape/edit workload would establish remaining CSV conflicts.
- **Effort:** Unknown — maintainer needs a current atomic/revision contract review to estimate remaining integration work.
- **Money:** None — retaining the existing CSV store and atomic-write helpers adds no database service or dependency purchase. Optional-connection charges are separate; maintenance work belongs in Effort.
- **Incompatible with:** B (Local database) as simultaneous choices for JH-OT-D05.
- **Needs first:** Preserve atomic_io, stable IDs and stale-revision checks already present.

#### Option B: Local database

- **What it is:** Move the main job store to SQLite. Define import/export so local workflows and private data remain controlled.
- **Unlocks:** Transactional local storage if implemented correctly.
- **Blocks:** Direct spreadsheet-file edits as the main-store workflow.
- **Risks:** Migration could lose rows or break Sheets/CLI behavior; rehearse round trips and restore from a local backup. Likelihood is Unknown — round-trip migration and interrupted-write fixtures would establish row loss or compatibility failures.
- **Effort:** Unknown — maintainer needs a SQLite migration/export/rollback prototype and fixtures to size work.
- **Money:** Unknown — any incremental purchase needs the chosen SQLite driver’s license/dependencies and a migration measurement of database, backup and temporary-copy space against available local disk capacity. No database server or paid database service is specified; optional-connection charges are separate and migration/export work belongs in Effort.
- **Incompatible with:** A (Keep spreadsheets) as simultaneous choices for JH-OT-D05.
- **Needs first:** Approve migration, export compatibility, concurrent access and rollback tests before replacing CSV.

#### Trade-offs

| Axis | A (Suggested) | B |
|---|---|---|
| Primary editing | Spreadsheet files | Database plus explicit export |
| Transition | Keep current store | Migration and compatibility work |

- **Downstream impact:**
  - **Changes:** local_sync/storage/admin paths and integration outbox boundaries; a database change must respect CONTRIBUTING filesystem intent and FUTURE’s no-database-server rule.
  - **Unblocks:** A persistence follow-up after explicit maintainer choice; integration does not require redoing closed atomic-write work.
- **Cost of deferring:** Existing CSV with atomic writes stays; local work continues. Cost begins if integration relies on an unchosen transaction model; actual scaling need is Unknown — a concurrent workload fixture would settle it.
- **Worst case:** CSV proves unsuitable for the intended workload. Preserve jobs with locks/revisions, measure a synthetic workload and propose a reversible SQLite migration.
