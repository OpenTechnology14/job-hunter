"""
Atomic, locked file persistence (JH-010)
Shared by the scraper, the apply flow and the admin panel, which can touch
the same CSV/JSON files at the same time.

Contract (docs/proposals/PROPOSAL_RELEASE_AND_SAFETY_GAP_CLOSURE.md §9):
  - Writes go to a unique temp file in the destination directory, are
    flushed and fsynced, keep the existing file's permissions, and replace
    the target with os.replace(). On any failure the original stays intact
    and the temp file is removed.
  - A per-file lock (`<file>.lock`, works across processes) covers the whole
    read-modify-write, not just the final write.

Usage:
    from atomic_io import atomic_write_json, locked_update_csv
    locked_update_csv(path, SHEET_COLUMNS, lambda rows: rows + new_rows)
"""
import csv
import io
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
    import msvcrt

LOCK_TIMEOUT_SECONDS = 10.0


class LockTimeout(TimeoutError):
    pass


@contextmanager
def file_lock(path, timeout: float = LOCK_TIMEOUT_SECONDS):
    """Exclusive lock on `<path>.lock`; not re-entrant. Raises LockTimeout."""
    lock_path = Path(f"{path}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as fh:
        deadline = time.monotonic() + timeout
        while True:
            try:
                if fcntl:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise LockTimeout(f"Timed out waiting for {lock_path}")
                time.sleep(0.02)
        try:
            yield
        finally:
            if fcntl:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            else:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)


def atomic_write_text(path, text: str, encoding: str = "utf-8", newline: str = None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = None
    if path.exists():
        mode = path.stat().st_mode & 0o777
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline=newline) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def atomic_write_json(path, data, indent: int = 2):
    atomic_write_text(path, json.dumps(data, indent=indent))


def csv_columns(columns, rows) -> list:
    """`columns` plus any extra named columns present in `rows`, in first-seen
    order, so a column the user added in their spreadsheet is kept."""
    out = list(columns)
    seen = set(out)
    for row in rows:
        for key in row:
            if key is not None and key not in seen:
                seen.add(key)
                out.append(key)
    return out


def atomic_write_csv(path, rows, columns):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=csv_columns(columns, rows))
    writer.writeheader()
    writer.writerows(rows)
    atomic_write_text(path, buf.getvalue(), newline="")


def read_csv_rows(path) -> list:
    path = Path(path)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def locked_update_csv(path, columns, mutate):
    """Read, mutate and atomically rewrite a CSV under one lock.

    `mutate(rows)` returns the new row list, or None to leave the file as is.
    Returns the rows now on disk.
    """
    with file_lock(path):
        rows = read_csv_rows(path)
        new_rows = mutate(rows)
        if new_rows is None:
            return rows
        atomic_write_csv(path, new_rows, columns)
        return new_rows


def locked_update_json(path, default, mutate):
    """Read, mutate and atomically rewrite a JSON file under one lock.

    `default()` supplies the value only when the file is missing. A corrupt
    file raises (json.JSONDecodeError) instead of being silently replaced.
    `mutate(data)` returns the new value. Returns what was written.
    """
    path = Path(path)
    with file_lock(path):
        try:
            with open(path) as f:
                data = json.load(f)
        except FileNotFoundError:
            data = default()
        new_data = mutate(data)
        atomic_write_json(path, new_data)
        return new_data
