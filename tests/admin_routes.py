"""
Admin route contract tests (JH-013), offline.

Copies the project's code into a temporary project tree and runs the Flask
app from there, so every path the handlers touch (PROJECT_ROOT, profiles/,
output/, and the __file__-relative roots in ai_training.py / ats_fields.py)
lands in the temp tree. Nothing reads or writes the real repo's profiles or
output. No network; no subprocess is started by the GET routes covered here.

Every route in docs/API_ROUTE_AUDIT_LEDGER.md is covered (phase 1: GET
routes; phase 2: mutating routes). The scrape route's subprocess and thread
are stubbed, so no scrape ever runs. A new route can't go untested silently:
the ledger check fails if a route is neither covered nor in PHASE2_PENDING.

Run directly (prints JSON results) or via `python run_tests.py --routes`.
"""
import atexit
import io
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Routes not yet covered. Must stay empty: the ledger check fails otherwise.
PHASE2_PENDING = set()  # every route is covered (phase 2 done 2026-11-07)

PDF_BYTES = b"%PDF-1.4\n% synthetic test resume\n%%EOF\n"


def build_tree():
    """Temp project tree: code copied, synthetic profile + output fixtures."""
    root = Path(tempfile.mkdtemp(prefix="jh-routes-")).resolve()
    atexit.register(shutil.rmtree, root, ignore_errors=True)  # even if a case crashes
    for f in REPO.glob("*.py"):
        shutil.copy(f, root / f.name)
    for f in ("requirements.txt", "form_config_example.json"):
        if (REPO / f).exists():
            shutil.copy(REPO / f, root / f)
    shutil.copytree(REPO / "admin", root / "admin",
                    ignore=shutil.ignore_patterns("__pycache__", "*.lock"))
    (root / "profiles").mkdir()
    shutil.copy(REPO / "profiles" / "__init__.py", root / "profiles" / "__init__.py")
    shutil.copy(REPO / "profiles" / "example_profile.py", root / "profiles" / "synthetic.py")
    shutil.copy(REPO / "profiles" / "example_profile.py", root / "profiles" / "example_profile.py")

    out = root / "output" / "synthetic"
    (out / "resumes").mkdir(parents=True)
    (out / "resumes" / "synthetic.pdf").write_bytes(PDF_BYTES)
    (out / "form_config.json").write_text(json.dumps({"custom_fields": [{"pattern": "synthetic", "value": "x"}], "select_defaults": []}))
    (out / "run_log.json").write_text(json.dumps([{"type": "api", "status": "completed"}]))
    # Sentinel one level above output/: must never be reachable through a profile segment.
    (root / "form_config.json").write_text(json.dumps({"LEAK": "outside-output"}))
    (root / "output" / "jobs.csv").write_text("Job Title\nLEAK-outside-profile\n")
    return root


def write_jobs(server, root):
    import atomic_io
    out = root / "output" / "synthetic"
    rows = []
    for title, company, apply_, wt in [("Synthetic Engineer", "Acme Test", "Y", "Remote"),
                                       ("Synthetic Analyst", "Beta Test", "", "On-site")]:
        r = {c: "" for c in server.SHEET_COLUMNS}
        r.update({"Job Title": title, "Company": company, "Apply": apply_, "Work Type": wt,
                  "Source": "Fixture", "Role Category": "Synthetic",
                  "URL": f"https://jobs.example.test/{title.split()[-1].lower()}?utm_source=feed"})
        rows.append(r)
    atomic_io.atomic_write_csv(out / "jobs.csv", rows, server.SHEET_COLUMNS)
    b = {c: "" for c in server.BROWSER_COLUMNS}
    b.update({"Job Title": "Synthetic Browser Role", "Apply": "Done"})
    atomic_io.atomic_write_csv(out / "browser_jobs.csv", [b], server.BROWSER_COLUMNS)


def server_routes(server):
    seen = set()
    for rule in server.app.url_map.iter_rules():
        if rule.endpoint == "static":   # Flask's built-in static route, not ours
            continue
        for m in rule.methods - {"HEAD", "OPTIONS"}:
            seen.add((m, rule.rule))
    return seen


def ledger_routes():
    text = (REPO / "docs" / "API_ROUTE_AUDIT_LEDGER.md").read_text()
    return {(m, p) for m, p in re.findall(r"^\| (GET|POST|PUT|PATCH|DELETE) \| `([^`]+)`", text, re.M)}


def run():
    root = build_tree()
    sys.path.insert(0, str(root / "admin"))
    sys.path.insert(0, str(root))
    import server  # the temp copy
    assert Path(server.__file__).resolve().is_relative_to(root), server.__file__
    write_jobs(server, root)
    c = server.app.test_client()
    results = []

    def case(route, name, fn):
        try:
            fn()
            results.append({"route": route, "case": name, "ok": True})
        except AssertionError as e:
            results.append({"route": route, "case": name, "ok": False, "error": str(e)})
        except Exception as e:
            results.append({"route": route, "case": name, "ok": False, "error": f"{type(e).__name__}: {e}"})

    def get(url):
        r = c.get(url)
        return r.status_code, (r.get_json(silent=True) if r.is_json else r.data)

    R = {}  # route -> covered

    def cover(method, rule):
        R[(method, rule)] = True
        return rule

    # ── UI / static ──
    rt = cover("GET", "/")
    case(rt, "serves index.html", lambda: (lambda s, b: (assert_(s == 200, s), assert_(b"<html" in b.lower(), "no html")))(*get("/")))
    rt = cover("GET", "/static/<path:filename>")
    case(rt, "serves a static file", lambda: assert_(get("/static/index.html")[0] == 200, "static index"))
    case(rt, "no escape from static dir", lambda: assert_(get("/static/..%2Fserver.py")[0] == 404, get("/static/..%2Fserver.py")[0]))

    # ── profiles ──
    rt = cover("GET", "/api/profiles")
    def profiles_list():
        s, b = get("/api/profiles")
        assert s == 200, s
        assert [p["name"] for p in b] == ["synthetic"], b
        p = b[0]
        assert (p["job_count"], p["browser_job_count"], p["resume_count"]) == (2, 1, 1), p
    case(rt, "lists synthetic profile with counts", profiles_list)

    rt = cover("GET", "/api/profiles/<name>")
    case(rt, "200 with profile sections", lambda: (lambda s, b: (assert_(s == 200, s), assert_({"user_profile", "role_profiles", "search_settings"} <= set(b), b)))(*get("/api/profiles/synthetic")))
    case(rt, "404 for unknown profile", lambda: assert_(get("/api/profiles/nope")[0] == 404, "expected 404"))

    rt = cover("GET", "/api/profiles/<name>/location")
    case(rt, "200 location filter", lambda: (lambda s, b: (assert_(s == 200, s), assert_("include_remote" in b, b)))(*get("/api/profiles/synthetic/location")))
    case(rt, "404 for unknown profile", lambda: assert_(get("/api/profiles/nope/location")[0] == 404, "expected 404"))

    rt = cover("GET", "/api/profiles/<name>/search-strings")
    case(rt, "200 per-role strings, no network", lambda: (lambda s, b: (assert_(s == 200, s), assert_(isinstance(b.get("roles"), dict) and b["roles"], b)))(*get("/api/profiles/synthetic/search-strings")))
    case(rt, "404 for unknown profile", lambda: assert_(get("/api/profiles/nope/search-strings")[0] == 404, "expected 404"))

    rt = cover("GET", "/api/profiles/<name>/roles")
    case(rt, "200 roles dict", lambda: (lambda s, b: (assert_(s == 200, s), assert_(isinstance(b.get("roles"), dict) and b["roles"], b)))(*get("/api/profiles/synthetic/roles")))
    case(rt, "404 for unknown profile", lambda: assert_(get("/api/profiles/nope/roles")[0] == 404, "expected 404"))

    # ── jobs ──
    rt = cover("GET", "/api/jobs/<profile>")
    def jobs_list():
        s, b = get("/api/jobs/synthetic")
        assert s == 200 and b["total"] == 2 and [j["_index"] for j in b["jobs"]] == [0, 1], b
        assert b["columns"] == server.SHEET_COLUMNS
    case(rt, "lists api jobs with _index", jobs_list)
    case(rt, "source=browser", lambda: assert_(get("/api/jobs/synthetic?source=browser")[1]["total"] == 1, "browser total"))
    case(rt, "filters: apply, work_type, search", lambda: (
        assert_(get("/api/jobs/synthetic?apply=y")[1]["total"] == 1, "apply filter"),
        assert_(get("/api/jobs/synthetic?work_type=Remote")[1]["total"] == 1, "work_type filter"),
        assert_(get("/api/jobs/synthetic?search=beta")[1]["total"] == 1, "search filter")))
    case(rt, "unknown profile is empty, not an error", lambda: assert_(get("/api/jobs/nope")[1]["total"] == 0, "expected empty"))

    rt = cover("GET", "/api/jobs/<profile>/stats")
    def stats():
        s, b = get("/api/jobs/synthetic/stats")
        assert s == 200 and b["api"]["total"] == 2 and b["api"]["approved"] == 1 and b["api"]["remote"] == 1, b
        assert b["browser"]["applied"] == 1, b
    case(rt, "api + browser stats", stats)

    rt = cover("GET", "/api/scrape/status")
    case(rt, "nothing running", lambda: assert_(get("/api/scrape/status")[1] == {"running": []}, "running"))

    # ── form config / resumes / history ──
    rt = cover("GET", "/api/form-config/<profile>")
    case(rt, "returns the profile's config", lambda: assert_(get("/api/form-config/synthetic")[1]["custom_fields"][0]["pattern"] == "synthetic", "profile config"))
    case(rt, "falls back to the example config", lambda: assert_("custom_fields" in get("/api/form-config/nope")[1], "fallback"))

    rt = cover("GET", "/api/resumes/<profile>")
    case(rt, "lists PDFs", lambda: assert_([r["filename"] for r in get("/api/resumes/synthetic")[1]] == ["synthetic.pdf"], "resume list"))
    case(rt, "unknown profile is an empty list", lambda: assert_(get("/api/resumes/nope")[1] == [], "expected []"))

    rt = cover("GET", "/api/resumes/<profile>/<filename>")
    def serve_pdf():
        r = c.get("/api/resumes/synthetic/synthetic.pdf")
        assert r.status_code == 200 and r.mimetype == "application/pdf" and r.data == PDF_BYTES, (r.status_code, r.mimetype)
    case(rt, "serves the PDF", serve_pdf)
    case(rt, "404 for a missing file", lambda: assert_(get("/api/resumes/synthetic/missing.pdf")[0] == 404, "expected 404"))

    rt = cover("GET", "/api/history/<profile>")
    case(rt, "returns the run log", lambda: assert_(get("/api/history/synthetic")[1] == [{"type": "api", "status": "completed"}], "history"))
    case(rt, "unknown profile is an empty list", lambda: assert_(get("/api/history/nope")[1] == [], "expected []"))

    rt = cover("GET", "/api/ai-training/<profile>")
    case(rt, "200 platforms + setup", lambda: (lambda s, b: (assert_(s == 200, s), assert_(len(b["platforms"]) > 0 and "setup" in b, b)))(*get("/api/ai-training/synthetic")))
    case(rt, "404 for unknown profile", lambda: assert_(get("/api/ai-training/nope")[0] == 404, "expected 404"))
    case(rt, "characterization: GET writes the tracker file", lambda: assert_((root / "output" / "synthetic" / "ai_training.json").exists(), "tracker not written"))

    # ── system ──
    rt = cover("GET", "/api/setup")
    def setup():
        s, b = get("/api/setup")
        assert s == 200 and b["profiles"]["ok"] is True and "synthetic" in b["profile_details"], b
        assert b["profile_details"]["synthetic"]["has_resumes"] is True, b
    case(rt, "reports checks for the temp tree", setup)
    rt = cover("GET", "/api/mode")
    case(rt, "local mode", lambda: assert_(get("/api/mode")[1] == {"deployed": False}, "mode"))
    rt = cover("GET", "/api/all-users")
    def all_users():
        s, b = get("/api/all-users")
        assert s == 200 and len(b) == 1, b
        u = b[0]
        assert (u["profile"], u["api_jobs"], u["approved"], u["applied"]) == ("synthetic", 2, 1, 1), u
    case(rt, "one user with counts", all_users)

    # ── job edits: stable id, revision, conflict (JH-010 follow-up) ──
    import atomic_io
    jobs_csv = root / "output" / "synthetic" / "jobs.csv"

    def patch(url, body):
        r = c.patch(url, json=body)
        return r.status_code, r.get_json(silent=True)

    def listing():
        return {j["Job Title"]: j for j in get("/api/jobs/synthetic")[1]["jobs"]}

    rt = cover("PATCH", "/api/jobs/<profile>/<int:index>")
    def ids_stable():
        a, b = listing(), listing()
        eng = a["Synthetic Engineer"]
        assert eng["_id"].startswith("j_") and eng["_id"] == b["Synthetic Engineer"]["_id"], eng
        assert eng["_rev"] == b["Synthetic Engineer"]["_rev"], "rev must be stable across reads"
        canon = server._job_id({"Source": "Fixture", "URL": "HTTPS://Jobs.Example.Test/engineer/?utm_campaign=z"})
        assert canon == eng["_id"], "canonical URL must ignore case, trailing slash and utm_*"
    case(rt, "_id/_rev are stable; _id uses the canonical URL", ids_stable)

    def edit_lands_after_reorder():
        eng = listing()["Synthetic Engineer"]
        rows = atomic_io.read_csv_rows(jobs_csv)          # a scrape inserts a new row on top
        new = {k: "" for k in server.SHEET_COLUMNS}; new.update({"Job Title": "Inserted By Scrape", "URL": "https://jobs.example.test/new"})
        atomic_io.atomic_write_csv(jobs_csv, [new] + rows, server.SHEET_COLUMNS)
        s, b = patch(f"/api/jobs/synthetic/{eng['_index']}", {"Notes": "edited", "_id": eng["_id"], "_rev": eng["_rev"]})
        assert s == 200 and b["row"]["Job Title"] == "Synthetic Engineer" and b["row"]["_index"] == 1, (s, b)
        after = listing()
        assert after["Synthetic Engineer"]["Notes"] == "edited" and after["Inserted By Scrape"]["Notes"] == "", after
        assert b["row"]["_id"] == eng["_id"] and b["row"]["_rev"] != eng["_rev"], "id kept, rev changed"
    case(rt, "edit by _id lands on the right job after a reorder", edit_lands_after_reorder)

    def stale_rev_conflicts():
        eng = listing()["Synthetic Engineer"]
        patch(f"/api/jobs/synthetic/{eng['_index']}", {"Apply": "N", "_id": eng["_id"], "_rev": eng["_rev"]})  # someone else
        before = jobs_csv.read_bytes()
        s, b = patch(f"/api/jobs/synthetic/{eng['_index']}", {"Apply": "Y", "_id": eng["_id"], "_rev": eng["_rev"]})
        assert s == 409 and b["error"] == "conflict" and b["current"]["Apply"] == "N", (s, b)
        assert jobs_csv.read_bytes() == before, "a conflicting edit must not write"
    case(rt, "stale _rev -> 409 with the current row, nothing written", stale_rev_conflicts)

    case(rt, "unknown _id -> 404", lambda: assert_(patch("/api/jobs/synthetic/0", {"Notes": "x", "_id": "j_000000000000"})[0] == 404, "expected 404"))
    def legacy_index():
        s, b = patch("/api/jobs/synthetic/0", {"Notes": "by index"})
        assert s == 200 and b["row"]["Notes"] == "by index" and "_id" in b["row"], (s, b)
        assert patch("/api/jobs/synthetic/99", {"Notes": "x"})[0] == 400, "bad index still 400"
    case(rt, "index-only PATCH still works (compatibility)", legacy_index)
    def ambiguous():
        rows = atomic_io.read_csv_rows(jobs_csv)
        atomic_io.atomic_write_csv(jobs_csv, rows + [dict(rows[0])], server.SHEET_COLUMNS)   # duplicate row
        dup_id = server._job_id(rows[0])
        s, b = patch("/api/jobs/synthetic/0", {"Notes": "x", "_id": dup_id})
        atomic_io.atomic_write_csv(jobs_csv, rows, server.SHEET_COLUMNS)
        assert s == 409 and b["error"] == "ambiguous", (s, b)
    case(rt, "duplicate rows -> 409 ambiguous, not a guess", ambiguous)

    rt = cover("PATCH", "/api/jobs/<profile>/bulk")
    def bulk_all_or_nothing():
        jobs = listing()
        a, b = jobs["Synthetic Engineer"], jobs["Synthetic Analyst"]
        before = jobs_csv.read_bytes()
        s, r = patch("/api/jobs/synthetic/bulk", {"items": [{"_id": a["_id"], "_rev": a["_rev"]}, {"_id": b["_id"], "_rev": "stale0000000"}], "updates": {"Notes": "bulk"}})
        assert s == 409 and len(r["conflicts"]) == 1 and jobs_csv.read_bytes() == before, (s, r)
        s, r = patch("/api/jobs/synthetic/bulk", {"items": [{"_id": a["_id"], "_rev": a["_rev"]}, {"_id": b["_id"], "_rev": b["_rev"]}], "updates": {"Notes": "bulk"}})
        assert s == 200 and r["updated"] == 2, (s, r)
        assert all(listing()[t]["Notes"] == "bulk" for t in ("Synthetic Engineer", "Synthetic Analyst"))
    case(rt, "bulk with items is all-or-nothing on conflict", bulk_all_or_nothing)
    def bulk_legacy():
        s, r = patch("/api/jobs/synthetic/bulk", {"indices": [0, 99], "updates": {"Notes": "legacy"}})
        assert s == 200 and r["updated"] == 1, (s, r)
    case(rt, "bulk by indices still works (compatibility)", bulk_legacy)

    # ── phase 2: mutating routes ──
    profiles = root / "profiles"

    def send(method, url, **kw):
        r = c.open(url, method=method, **kw)
        return r.status_code, r.get_json(silent=True)

    rt = cover("PATCH", "/api/profiles/<name>/search-settings")
    def settings_ok():
        s, b = send("PATCH", "/api/profiles/synthetic/search-settings", json={"web_search": True, "stale_days": 7, "not_allowed": 1})
        src = (profiles / "synthetic.py").read_text()
        assert s == 200 and '"web_search": True' in src and '"stale_days": 7' in src and "not_allowed" not in src, (s, b)
    case(rt, "whitelisted keys written, unknown keys ignored", settings_ok)
    case(rt, "non-integer value -> 400, not 500", lambda: assert_(send("PATCH", "/api/profiles/synthetic/search-settings", json={"stale_days": "soon"})[0] == 400, "expected 400"))
    case(rt, "unknown profile -> 404", lambda: assert_(send("PATCH", "/api/profiles/nope/search-settings", json={"web_search": True})[0] == 404, "expected 404"))
    case(rt, "the example template can't be edited", lambda: assert_(send("PATCH", "/api/profiles/example_profile/search-settings", json={"web_search": True})[0] == 403, "expected 403"))

    rt = cover("POST", "/api/scrape/<profile>")
    spawned = []
    class _InlineThread:  # run the job synchronously, with subprocess.run stubbed
        def __init__(self, target, args=(), daemon=None): self.target, self.args = target, args
        def start(self): self.target(*self.args)
    real_thread, real_run = server.threading.Thread, server.subprocess.run
    server.threading.Thread = _InlineThread
    server.subprocess.run = lambda cmd, **kw: spawned.append(cmd) or __import__("subprocess").CompletedProcess(cmd, 0, "ok", "")
    try:
        def scrape_ok():
            s, b = send("POST", "/api/scrape/synthetic", json={"type": "api", "role": "software-engineer"})
            assert s == 200 and b["status"] == "started", (s, b)
            cmd = spawned[-1]
            assert cmd[1] == "run_scrape.py" and cmd[2:4] == ["--profile", "synthetic"] and "--role" in cmd, cmd
            assert str(root) in cmd[0], f"must use the project's own venv path: {cmd[0]}"
            assert get("/api/history/synthetic")[1][-1]["status"] == "complete", "run log entry"
        case(rt, "starts run_scrape.py for the profile (stubbed) and logs it", scrape_ok)
        def scrape_busy():
            server._running["synthetic_api"] = True
            try:
                assert send("POST", "/api/scrape/synthetic", json={"type": "api"})[0] == 409, "expected 409"
            finally:
                server._running.pop("synthetic_api", None)
        case(rt, "already running -> 409", scrape_busy)
        case(rt, "non-JSON (cross-site form) post -> 415, nothing spawned",
             lambda: (lambda n: (assert_(send("POST", "/api/scrape/synthetic", data="type=api", content_type="text/plain")[0] == 415, "expected 415"),
                                 assert_(len(spawned) == n, "spawned")))(len(spawned)))
    finally:
        server.threading.Thread, server.subprocess.run = real_thread, real_run

    rt = cover("PUT", "/api/form-config/<profile>")
    def form_put():
        cfg = {"custom_fields": [{"pattern": "nickname", "value": "Syn"}], "select_defaults": []}
        s, _ = send("PUT", "/api/form-config/synthetic", json=cfg)
        assert s == 200 and get("/api/form-config/synthetic")[1] == cfg, s
    case(rt, "replaces the config", form_put)
    case(rt, "non-object or wrong shape -> 400", lambda: (
        assert_(send("PUT", "/api/form-config/synthetic", json=None)[0] in (400, 415), "null body"),
        assert_(send("PUT", "/api/form-config/synthetic", json=[1, 2])[0] == 400, "list body"),
        assert_(send("PUT", "/api/form-config/synthetic", json={"custom_fields": "x"})[0] == 400, "custom_fields not a list")))

    rt = cover("POST", "/api/form-config/<profile>/seed")
    def seed():
        s, b = send("POST", "/api/form-config/synthetic/seed", json={"reset": True})
        cfg = json.loads((root / "output" / "synthetic" / "form_config.json").read_text())
        assert s == 200 and b["ok"] and len(cfg["custom_fields"]) > 5, (s, b)
    case(rt, "seeds from the ATS catalog into the temp tree", seed)
    case(rt, "unknown profile -> 404", lambda: assert_(send("POST", "/api/form-config/nope/seed", json={})[0] == 404, "expected 404"))

    rt = cover("PATCH", "/api/ai-training/<profile>/platforms/<platform_id>")
    plat = get("/api/ai-training/synthetic")[1]["platforms"][0]["id"]
    statuses = get("/api/ai-training/synthetic")[1]["statuses"]
    def plat_ok():
        s, b = send("PATCH", f"/api/ai-training/synthetic/platforms/{plat}", json={"status": statuses[-1], "notes": "synthetic"})
        assert s == 200 and b["status"] == statuses[-1] and b["notes"] == "synthetic", (s, b)
    case(rt, "updates status and notes", plat_ok)
    case(rt, "bad status -> 400; unknown platform -> 404", lambda: (
        assert_(send("PATCH", f"/api/ai-training/synthetic/platforms/{plat}", json={"status": "Bogus"})[0] == 400, "bad status"),
        assert_(send("PATCH", "/api/ai-training/synthetic/platforms/nope", json={})[0] == 404, "unknown platform")))

    rt = cover("POST", "/api/ai-training/<profile>/generate-resume")
    case(rt, "410 Gone (JH-015)", lambda: assert_(send("POST", "/api/ai-training/synthetic/generate-resume")[0] == 410, "expected 410"))

    rt = cover("POST", "/api/profiles")
    def create():
        s, b = send("POST", "/api/profiles", json={"name": "Second Person!", "user_info": {"name": "Second Person", "email": "second@example.test"}})
        assert s in (200, 201) and (profiles / "secondperson.py").exists(), (s, b)
        assert (root / "output" / "secondperson" / "resumes").is_dir(), "output dirs"
        assert send("POST", "/api/profiles", json={"name": "secondperson"})[0] == 409, "duplicate"
        assert send("POST", "/api/profiles", json={"name": "!"})[0] == 400, "bad name"
    case(rt, "creates a sanitized profile; duplicate 409; bad name 400", create)

    rt = cover("POST", "/api/profiles/<name>/roles")
    def add_role():
        s, b = send("POST", "/api/profiles/secondperson/roles", json={"role_id": "Data-Eng", "label": "Data Eng", "salary_min": 90000, "salary_max": 120000, "search_queries": ["data engineer"]})
        assert s == 200 and b["role_id"] == "data-eng", (s, b)
        assert "data-eng" in get("/api/profiles/secondperson/roles")[1]["roles"], "role listed"
        assert send("POST", "/api/profiles/secondperson/roles", json={"role_id": "x2", "search_queries": []})[0] == 400, "no queries"
        assert send("POST", "/api/profiles/secondperson/roles", json={"role_id": "x3", "salary_min": "lots", "search_queries": ["a"]})[0] == 400, "non-integer salary"
    case(rt, "adds a role; validation errors are 400", add_role)

    rt = cover("PUT", "/api/profiles/<name>/roles/<role_id>")
    def update_role():
        s, _ = send("PUT", "/api/profiles/secondperson/roles/data-eng", json={"salary_max": 130000})
        assert s == 200 and get("/api/profiles/secondperson/roles")[1]["roles"]["data-eng"]["salary_max"] == 130000, s
        assert send("PUT", "/api/profiles/secondperson/roles/missing", json={})[0] == 404, "missing role"
        assert send("PUT", "/api/profiles/secondperson/roles/data-eng", json={"salary_min": "x"})[0] == 400, "non-integer salary"
    case(rt, "updates a role; missing 404; bad value 400", update_role)

    rt = cover("DELETE", "/api/profiles/<name>/roles/<role_id>")
    def delete_role():
        s, b = send("DELETE", "/api/profiles/secondperson/roles/data-eng")
        assert s == 200 and b["remaining_roles"] == 0, (s, b)
        assert send("DELETE", "/api/profiles/secondperson/roles/data-eng")[0] == 404, "already gone"
    case(rt, "deletes a role; second delete 404", delete_role)

    rt = cover("POST", "/api/resumes/<profile>/upload")
    def upload():
        r = c.post("/api/resumes/synthetic/upload", data={"file": (io.BytesIO(PDF_BYTES), "My Resume (2).pdf")}, content_type="multipart/form-data")
        b = r.get_json()
        assert r.status_code == 200 and b["filename"] == "My_Resume__2_.pdf", b
        assert (root / "output" / "synthetic" / "resumes" / "My_Resume__2_.pdf").read_bytes() == PDF_BYTES
        bad = c.post("/api/resumes/synthetic/upload", data={"file": (io.BytesIO(b"x"), "notes.txt")}, content_type="multipart/form-data")
        assert bad.status_code == 400, bad.status_code
        assert c.post("/api/resumes/synthetic/upload", data={}, content_type="multipart/form-data").status_code == 400, "no file"
    case(rt, "saves a sanitized PDF name; non-PDF 400; missing file 400", upload)

    rt = cover("DELETE", "/api/resumes/<profile>/<filename>")
    def delete_resume():
        assert send("DELETE", "/api/resumes/synthetic/My_Resume__2_.pdf")[0] == 200, "delete"
        assert not (root / "output" / "synthetic" / "resumes" / "My_Resume__2_.pdf").exists(), "file still there"
        assert send("DELETE", "/api/resumes/synthetic/My_Resume__2_.pdf")[0] == 404, "second delete"
        assert send("DELETE", "/api/resumes/synthetic/..")[0] == 404, "dotdot"
        assert (root / "output" / "synthetic").is_dir(), "profile dir must survive"
    case(rt, "deletes a resume; missing/.. 404", delete_resume)

    rt = cover("DELETE", "/api/profiles/<name>")
    def delete_profile():
        s, b = send("DELETE", "/api/profiles/secondperson")
        assert s == 200 and not (profiles / "secondperson.py").exists(), (s, b)
        assert (root / "output" / "secondperson").is_dir(), "output data must be kept"
        assert send("DELETE", "/api/profiles/secondperson")[0] == 404, "second delete"
    case(rt, "deletes the profile file, keeps output data", delete_profile)
    def reserved():
        for name in ("__init__", "example_profile"):
            s, _ = send("DELETE", f"/api/profiles/{name}")
            assert s == 403 and (profiles / f"{name}.py").exists(), f"{name}: {s}"
    case(rt, "reserved files (__init__, example template) can't be deleted", reserved)

    # ── path safety across profile-scoped GET routes ──
    case("(path safety)", "profile segment can't reach outside output/", path_safety(get))
    case("(path safety)", "resume filename '..' is 404, not a crash", lambda: assert_(get("/api/resumes/synthetic/..")[0] == 404, get("/api/resumes/synthetic/..")[0]))

    # ── ledger ──
    srv, led = server_routes(server), ledger_routes()
    covered = set(R)
    results.append({"route": "(ledger)", "case": "server routes == ledger",
                    "ok": srv == led, "error": f"server-only {sorted(srv - led)}; ledger-only {sorted(led - srv)}"})
    results.append({"route": "(ledger)", "case": "every route covered or pending phase 2",
                    "ok": srv == covered | PHASE2_PENDING and not (covered & PHASE2_PENDING),
                    "error": f"unmapped {sorted(srv - covered - PHASE2_PENDING)}; both {sorted(covered & PHASE2_PENDING)}"})

    shutil.rmtree(root, ignore_errors=True)
    return {"covered": len(covered), "pending": len(PHASE2_PENDING), "results": results}


def path_safety(get):
    def check():
        for url in ("/api/form-config/%2E%2E", "/api/jobs/%2E%2E", "/api/history/%2E%2E",
                    "/api/jobs/%2E%2E/stats", "/api/resumes/%2E%2E"):
            s, b = get(url)
            body = json.dumps(b) if not isinstance(b, (bytes, bytearray)) else b.decode("utf-8", "replace")
            assert "LEAK" not in body, f"{url} returned data from outside output/: {body[:120]}"
            assert s in (400, 404), f"{url} -> {s} (expected 400/404)"
    return check


def assert_(cond, msg):
    if not cond:
        raise AssertionError(msg)


if __name__ == "__main__":
    print(json.dumps(run()))
