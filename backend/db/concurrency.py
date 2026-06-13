"""Bounded retry helpers for transient SQLite write-lock contention.

WAL + ``busy_timeout`` (see ``db/base.py``) absorb sub-second write contention
at the driver level, which resolves the reported failure (DEBUG_LOG ERR-015).
These helpers are the bounded *backstop* for the residual window where a writer
can still observe a transient "database is locked" — e.g. ``busy_timeout``
exceeded by an unusually long write, or a WAL-checkpoint race. They never mask
a real error: non-lock failures and the final lock (after the retry budget is
spent) propagate.
"""

import time
from typing import Callable, Optional, TypeVar

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

T = TypeVar("T")

#: Total attempts (1 initial + up to attempts-1 retries). The real waiting is
#: done by ``busy_timeout``; this only covers the rare residual lock, so the
#: budget is small.
DEFAULT_ATTEMPTS = 5

#: First backoff sleep in seconds; doubles each retry (0.05, 0.1, 0.2, 0.4).
BASE_DELAY = 0.05


def _is_locked(exc: OperationalError) -> bool:
    """True for SQLite's transient busy/locked errors (worth retrying)."""
    message = str(exc).lower()
    return "database is locked" in message or "database table is locked" in message


def run_with_retry(
    operation: Callable[[], T],
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay: float = BASE_DELAY,
) -> T:
    """Run a self-contained unit of work, retrying transient SQLite locks.

    ``operation`` MUST own its session lifecycle (open → commit/rollback →
    close) and be safe to call repeatedly, since a transient lock simply
    re-invokes it from scratch. Use this for worker-thread writers that build
    their own session (e.g. the WebSocket persist path).

    Args:
        operation: zero-arg callable performing one complete write unit.
        attempts: total attempts including the first.
        base_delay: seconds for the first backoff; doubles per retry.

    Returns:
        Whatever ``operation`` returns on success.

    Raises:
        OperationalError: a non-lock error (immediately) or a persistent lock
            after the retry budget is exhausted.
    """
    for attempt in range(attempts):
        try:
            return operation()
        except OperationalError as exc:
            if attempt == attempts - 1 or not _is_locked(exc):
                raise
            time.sleep(base_delay * (2 ** attempt))
    # Unreachable: the loop either returns or raises on the final attempt.
    raise AssertionError("run_with_retry exhausted without returning or raising")


def commit_with_retry(
    session: Session,
    *,
    restage: Optional[Callable[[], None]] = None,
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay: float = BASE_DELAY,
) -> None:
    """Commit ``session``, retrying transient SQLite write locks.

    On a transient lock the session is rolled back, ``restage`` (if given) is
    re-invoked to rebuild the unit's pending state onto the now-clean session,
    and the commit is retried after a bounded backoff.

    ``restage`` MUST reproduce ALL pending mutations from scratch — re-add ORM
    rows, re-create pending parents, re-apply field bumps — because a rollback
    discards them. Idiomatic use stages once via the same callable, then hands
    it in as ``restage``::

        def _stage():
            session.add(row)
            parent.count += 1
        _stage()
        commit_with_retry(session, restage=_stage)

    Pure computation (e.g. the generation walk) must happen OUTSIDE ``restage``
    so a retry never re-runs it.

    Raises:
        OperationalError: a non-lock error, or a persistent lock after the
            retry budget is exhausted (the session is rolled back first).
    """
    for attempt in range(attempts):
        try:
            session.commit()
            return
        except OperationalError as exc:
            session.rollback()
            if attempt == attempts - 1 or not _is_locked(exc):
                raise
            if restage is not None:
                restage()
            time.sleep(base_delay * (2 ** attempt))
