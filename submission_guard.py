"""
Submission Guard (JH-003)
The only path to clicking a Submit button during auto-apply.

Contract (docs/proposals/PROPOSAL_RELEASE_AND_SAFETY_GAP_CLOSURE.md §7.2):
  - dry_run=True can never mint a token or invoke the submit callback.
  - A token is scoped to one job and one page fingerprint.
  - A token expires after a short window and is consumed exactly once,
    whether or not the click succeeds.
  - Navigation, a page change, a failure or a cancellation invalidates it.

Usage:
    guard = SubmissionGuard(dry_run=dry_run)
    fp = current_page_fingerprint(page, label)
    token = guard.request_confirmation(job_id, fp)      # asks the user
    if token:
        guard.submit_once(token, job_id, current_page_fingerprint(page, label),
                          submit_button.click)
"""
import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Callable, Optional


DEFAULT_TTL_SECONDS = 120


def current_page_fingerprint(page, submit_label: str = "") -> str:
    """Identify the page state a confirmation was given for.

    Built from the page URL (fragment dropped) and the visible submit label,
    so a navigation or a different form step yields a different fingerprint.
    """
    url = (getattr(page, "url", "") or "").split("#", 1)[0]
    raw = f"{url}\n{submit_label.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ConfirmationToken:
    value: str
    job_id: str
    page_fingerprint: str
    expires_at: float


class SubmissionGuard:
    def __init__(self, dry_run: bool, ttl_seconds: float = DEFAULT_TTL_SECONDS,
                 clock: Callable[[], float] = time.monotonic,
                 confirm: Optional[Callable[[str], str]] = None):
        self.dry_run = dry_run
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        # Resolve input() at call time so tests (and wrappers) can replace it.
        self._confirm = confirm or (lambda prompt: input(prompt))
        self._outstanding: Optional[ConfirmationToken] = None

    def request_confirmation(self, job_id: str, page_fingerprint: str,
                             prompt: str = "\n    🚀 SUBMIT? Enter to send, 's' to skip: "
                             ) -> Optional[ConfirmationToken]:
        """Ask the user; return a fresh single-use token, or None.

        Dry-run returns None without asking. Any earlier outstanding token is
        invalidated first, so only one confirmation is ever live.
        """
        self.invalidate()
        if self.dry_run:
            return None
        answer = self._confirm(prompt).strip().lower()
        if answer == "s":
            return None
        token = ConfirmationToken(
            value=secrets.token_hex(16),
            job_id=job_id,
            page_fingerprint=page_fingerprint,
            expires_at=self._clock() + self.ttl_seconds,
        )
        self._outstanding = token
        return token

    def submit_once(self, token: Optional[ConfirmationToken], job_id: str,
                    page_fingerprint: str, click: Callable[[], object]) -> bool:
        """Click Submit once if `token` is valid for this exact job and page.

        The outstanding token is consumed before any check, so a failed,
        repeated or stale call can never submit twice. That is fail-closed:
        *any* refused attempt also voids the live confirmation, and the user
        must confirm again. Returns True only when the click was made.
        """
        if self.dry_run or token is None:
            return False
        live = self._outstanding
        self._outstanding = None          # consumed (or invalid) either way
        if live is None or live.value != token.value:
            return False                  # unknown, replayed or invalidated
        if self._clock() > live.expires_at:
            return False                  # expired
        if live.job_id != job_id or live.page_fingerprint != page_fingerprint:
            return False                  # different job, or the page changed
        click()
        return True

    def invalidate(self) -> None:
        """Drop any outstanding confirmation (navigation, failure, cancel)."""
        self._outstanding = None
