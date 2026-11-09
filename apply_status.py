"""
Apply Status (JH-D07)
The values of the Apply column, and how every reader classifies them.

Owner decision (2026-11-09) — "Done" is split in two:
  Auto Applied  (auto_applied)  Job Hunter clicked Submit itself (guarded click)
  User Applied  (user_applied)  Job Hunter prepared the application; the user
                                clicked Submit by hand

The CSV stores the readable label. Historical "Done…" values are read as
Auto Applied; `--migrate` rewrites them and tags rows whose history is
ambiguous (not Easy Apply) with "needs-review" in Notes.

Usage:
    python apply_status.py --profile <name> --migrate --dry-run
    python apply_status.py --profile <name> --migrate
"""
from enum import Enum


class ApplyStatus(str, Enum):
    AUTO_APPLIED = "auto_applied"
    USER_APPLIED = "user_applied"

    @property
    def label(self) -> str:
        return LABELS[self]


LABELS = {
    ApplyStatus.AUTO_APPLIED: "Auto Applied",
    ApplyStatus.USER_APPLIED: "User Applied",
}

NEEDS_REVIEW_TAG = "needs-review: marked Done before 2026-11-09; confirm who clicked Submit"


def classify(value) -> str:
    """'auto_applied' | 'user_applied' | 'approved' | 'rejected' | 'pending'.

    Accepts CSV labels, Google Sheets labels ("✅ Auto Applied") and legacy
    "Done…" values (read as Auto Applied — the migration default)."""
    v = (value or "").strip().lstrip("✅").strip().upper()
    if v.startswith("AUTO APPLIED") or v.startswith("DONE") or v == "APPLIED":
        return ApplyStatus.AUTO_APPLIED.value
    if v.startswith("USER APPLIED"):
        return ApplyStatus.USER_APPLIED.value
    if v == "Y":
        return "approved"
    if v == "N":
        return "rejected"
    return "pending"


def is_applied(value) -> bool:
    return classify(value) in (ApplyStatus.AUTO_APPLIED.value, ApplyStatus.USER_APPLIED.value)


def is_protected(value) -> bool:
    """Rows that cleanup and retro-clean must never remove: approved or applied."""
    return classify(value) in ("approved", ApplyStatus.AUTO_APPLIED.value, ApplyStatus.USER_APPLIED.value)


def migrate_rows(rows):
    """Rewrite legacy Done rows. Returns (rows, summary). Idempotent.

    Every "Done…" becomes "Auto Applied" (can't be told apart afterwards).
    Rows whose Apply Method isn't Easy Apply may really have been finished by
    hand, so they also get a one-time needs-review tag in Notes. Nothing else
    changes; no row is added, removed or reordered.
    """
    migrated, flagged = 0, 0
    out = []
    for row in rows:
        row = dict(row)
        raw = (row.get("Apply") or "").strip()
        if raw.upper().startswith("DONE"):
            row["Apply"] = ApplyStatus.AUTO_APPLIED.label
            migrated += 1
            method = (row.get("Apply Method") or "").lower()
            if "easy apply" not in method:
                notes = (row.get("Notes") or "").strip()
                if NEEDS_REVIEW_TAG not in notes:
                    row["Notes"] = f"{notes} [{NEEDS_REVIEW_TAG}]".strip()
                flagged += 1
        out.append(row)
    return out, {"rows": len(rows), "migrated": migrated, "needs_review": flagged}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Apply-status migration (JH-D07)")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--migrate", action="store_true", help="Rewrite legacy Done rows")
    parser.add_argument("--dry-run", action="store_true", help="Report only; write nothing")
    args = parser.parse_args()
    if not args.migrate:
        parser.error("nothing to do: pass --migrate (optionally --dry-run)")
    import local_sync  # loads the profile named by --profile
    from atomic_io import file_lock
    with file_lock(local_sync.JOBS_FILE):
        rows = local_sync._read_all_rows()
        new_rows, summary = migrate_rows(rows)
        print(f"  {summary['rows']} rows · {summary['migrated']} Done → Auto Applied · "
              f"{summary['needs_review']} tagged needs-review")
        if args.dry_run:
            print("  Dry run: nothing written.")
        elif summary["migrated"]:
            local_sync._write_all_rows(new_rows)
            print(f"  ✅ Wrote {local_sync.JOBS_FILE}")
