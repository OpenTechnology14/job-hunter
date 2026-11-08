"""
Admin route contract tests (JH-013), offline.

Copies the project's code into a temporary project tree and runs the Flask
app from there, so every path the handlers touch (PROJECT_ROOT, profiles/,
output/, and the __file__-relative roots in ai_training.py / ats_fields.py)
lands in the temp tree. Nothing reads or writes the real repo's profiles or
output. No network; no subprocess is started by the GET routes covered here.

Phase 1: every read-only (GET) route. Mutating routes are listed in
PHASE2_PENDING and must still be mapped, so a new route can't go untested
silently: the ledger check fails if a route is neither covered nor pending.

Run directly (prints JSON results) or via `python run_tests.py --routes`.
"""
import atexit
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Mutating routes not yet covered (phase 2). Keep in ledger order.
PHASE2_PENDING = {
    ("PATCH", "/api/profiles/<name>/search-settings"),
    ("PATCH", "/api/jobs/<profile>/<int:index>"),
    ("PATCH", "/api/jobs/<profile>/bulk"),
    ("POST", "/api/scrape/<profile>"),
    ("PUT", "/api/form-config/<profile>"),
    ("POST", "/api/form-config/<profile>/seed"),
    ("PATCH", "/api/ai-training/<profile>/platforms/<platform_id>"),
    ("POST", "/api/ai-training/<profile>/generate-resume"),
    ("POST", "/api/profiles"),
    ("DELETE", "/api/profiles/<name>"),
    ("POST", "/api/profiles/<name>/roles"),
    ("PUT", "/api/profiles/<name>/roles/<role_id>"),
    ("DELETE", "/api/profiles/<name>/roles/<role_id>"),
    ("POST", "/api/resumes/<profile>/upload"),
    ("DELETE", "/api/resumes/<profile>/<filename>"),
}

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
                  "Source": "Fixture", "Role Category": "Synthetic"})
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
