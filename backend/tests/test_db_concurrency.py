"""Tests for SQLite concurrency hardening.

Regression coverage for DEBUG_LOG ERR-015: the WebSocket persist worker thread
and the HTTP request threadpool write the same SQLite file, and default SQLite
(rollback journal, busy_timeout=0) failed a competing writer immediately with
"database is locked" (-> HTTP 500). The fix is two-fold:

1. Per-connection PRAGMAs (db/base.py): WAL + busy_timeout + synchronous=NORMAL.
2. Bounded retry helpers (db/concurrency.py) as a backstop for the residual
   transient-lock window.
"""

import sqlite3

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config import settings
from db.base import engine
from db.concurrency import commit_with_retry, run_with_retry


def _locked() -> OperationalError:
    """An OperationalError that looks like SQLite's transient busy/locked."""
    return OperationalError("UPDATE gaskets ...", {}, sqlite3.OperationalError("database is locked"))


def _not_locked() -> OperationalError:
    """A non-transient OperationalError that must NOT be retried."""
    return OperationalError("UPDATE gaskets ...", {}, sqlite3.OperationalError("no such table: gaskets"))


class _FakeSession:
    """Minimal Session stand-in counting commit/rollback and failing N times."""

    def __init__(self, fail_times: int, error: OperationalError):
        self.fail_times = fail_times
        self.error = error
        self.commit_calls = 0
        self.rollback_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1
        if self.commit_calls <= self.fail_times:
            raise self.error

    def rollback(self) -> None:
        self.rollback_calls += 1


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Keep backoff deterministic and instant."""
    monkeypatch.setattr("db.concurrency.time.sleep", lambda *_: None)


# ---------------------------------------------------------------------------
# Per-connection PRAGMAs
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not settings.DATABASE_URL.startswith("sqlite"), reason="PRAGMAs are SQLite-only"
)
def test_sqlite_pragmas_applied_per_connection():
    """Every new connection comes up in WAL with a 5s busy timeout."""
    with engine.connect() as conn:
        journal = conn.execute(text("PRAGMA journal_mode")).scalar()
        busy = conn.execute(text("PRAGMA busy_timeout")).scalar()
        synchronous = conn.execute(text("PRAGMA synchronous")).scalar()

    assert str(journal).lower() == "wal"
    assert int(busy) == 5000
    assert int(synchronous) == 1  # NORMAL


# ---------------------------------------------------------------------------
# commit_with_retry
# ---------------------------------------------------------------------------

class TestCommitWithRetry:
    def test_succeeds_after_transient_locks(self):
        """A few transient locks are retried (with re-staging) then commit."""
        session = _FakeSession(fail_times=2, error=_locked())
        restage_calls = {"n": 0}

        commit_with_retry(session, restage=lambda: restage_calls.__setitem__("n", restage_calls["n"] + 1))

        assert session.commit_calls == 3  # 2 failures + 1 success
        assert session.rollback_calls == 2  # one per failed attempt
        assert restage_calls["n"] == 2  # re-staged before each retry

    def test_non_lock_error_propagates_immediately(self):
        """A non-transient error is not retried — it rolls back and raises."""
        session = _FakeSession(fail_times=99, error=_not_locked())
        restage_calls = {"n": 0}

        with pytest.raises(OperationalError):
            commit_with_retry(session, restage=lambda: restage_calls.__setitem__("n", restage_calls["n"] + 1))

        assert session.commit_calls == 1
        assert session.rollback_calls == 1
        assert restage_calls["n"] == 0

    def test_gives_up_after_budget_exhausted(self):
        """A persistent lock raises after the attempt budget, rolled back."""
        session = _FakeSession(fail_times=99, error=_locked())

        with pytest.raises(OperationalError):
            commit_with_retry(session, attempts=3)

        assert session.commit_calls == 3
        assert session.rollback_calls == 3

    def test_restage_optional(self):
        """restage is optional; commit still retries without it."""
        session = _FakeSession(fail_times=1, error=_locked())
        commit_with_retry(session)
        assert session.commit_calls == 2


# ---------------------------------------------------------------------------
# run_with_retry
# ---------------------------------------------------------------------------

class TestRunWithRetry:
    def test_succeeds_after_transient_locks(self):
        calls = {"n": 0}

        def operation():
            calls["n"] += 1
            if calls["n"] <= 2:
                raise _locked()
            return "ok"

        assert run_with_retry(operation) == "ok"
        assert calls["n"] == 3

    def test_non_lock_error_propagates_immediately(self):
        calls = {"n": 0}

        def operation():
            calls["n"] += 1
            raise _not_locked()

        with pytest.raises(OperationalError):
            run_with_retry(operation)
        assert calls["n"] == 1

    def test_gives_up_after_budget_exhausted(self):
        calls = {"n": 0}

        def operation():
            calls["n"] += 1
            raise _locked()

        with pytest.raises(OperationalError):
            run_with_retry(operation, attempts=4)
        assert calls["n"] == 4
