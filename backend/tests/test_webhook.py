"""The webhook endpoint and the background review pipeline (all I/O mocked)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models import AgentResult, Issue


@pytest.fixture
def mocks(monkeypatch):
    """Replace every outside dependency of the webhook module."""
    import app.routers.webhook as wh

    m = MagicMock()
    m.get_pr_files = AsyncMock(return_value=[{"filename": "a.py", "patch": "+x = 1"}])
    m.run_review = AsyncMock(
        return_value=(
            AgentResult(
                issues=[
                    Issue(file="a.py", line=3, severity="high", issue="SQL injection", suggestion="Use params"),
                    Issue(file="a.py", line=None, severity="low", issue="General note", suggestion="Fine"),
                ],
                summary="One serious problem.",
            ),
            1234,
        )
    )
    m.post_review_comment = AsyncMock()
    m.post_summary_comment = AsyncMock()
    m.insert_one = AsyncMock()
    monkeypatch.setattr(wh, "get_pr_files", m.get_pr_files)
    monkeypatch.setattr(wh, "run_review", m.run_review)
    monkeypatch.setattr(wh, "post_review_comment", m.post_review_comment)
    monkeypatch.setattr(wh, "post_summary_comment", m.post_summary_comment)
    monkeypatch.setattr(wh, "reviews_collection", MagicMock(insert_one=m.insert_one))
    return m


# ---------- security ----------

def test_bad_signature_returns_401_and_does_nothing(post_webhook, pr_payload, mocks):
    r = post_webhook(pr_payload, signature="sha256=deadbeef")
    assert r.status_code == 401
    mocks.get_pr_files.assert_not_called()


def test_missing_signature_returns_401(post_webhook, pr_payload, mocks):
    r = post_webhook(pr_payload, signature="")
    assert r.status_code == 401
    mocks.run_review.assert_not_called()


# ---------- routing ----------

def test_non_pull_request_event_is_ignored(post_webhook, pr_payload, mocks):
    r = post_webhook(pr_payload, event="push")
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"
    mocks.get_pr_files.assert_not_called()


def test_irrelevant_pr_action_is_ignored(post_webhook, pr_payload, mocks):
    pr_payload["action"] = "closed"
    r = post_webhook(pr_payload)
    assert r.json()["status"] == "ignored"
    mocks.run_review.assert_not_called()


@pytest.mark.parametrize("action", ["opened", "synchronize"])
def test_opened_and_synchronize_are_accepted(post_webhook, pr_payload, mocks, action):
    pr_payload["action"] = action
    r = post_webhook(pr_payload)
    assert r.status_code == 200
    assert r.json() == {"status": "accepted", "pr_number": 7}


# ---------- the background pipeline ----------

def test_pipeline_fetches_reviews_comments_and_saves(post_webhook, pr_payload, mocks):
    post_webhook(pr_payload)  # TestClient runs the background task before returning

    mocks.get_pr_files.assert_awaited_once_with("someone", "some-repo", 7)
    mocks.run_review.assert_awaited_once()

    # Only the issue that has a line number becomes an inline comment.
    assert mocks.post_review_comment.await_count == 1
    args = mocks.post_review_comment.await_args.args
    assert args[:6] == ("someone", "some-repo", 7, "abc123", "a.py", 3)
    assert "[HIGH] SQL injection" in args[6]
    assert "Use params" in args[6]

    # One summary comment mentioning the total issue count.
    mocks.post_summary_comment.assert_awaited_once()
    assert "Found **2** issue(s)" in mocks.post_summary_comment.await_args.args[3]


def test_review_is_saved_in_the_shape_the_dashboard_expects(post_webhook, pr_payload, mocks):
    post_webhook(pr_payload)

    saved = mocks.insert_one.await_args.args[0]
    assert saved["repo"] == "someone/some-repo"
    assert saved["pr_number"] == 7
    assert saved["pr_title"] == "Add login"
    assert saved["commit_id"] == "abc123"
    assert saved["latency_ms"] == 1234
    assert saved["summary"] == "One serious problem."
    assert len(saved["issues"]) == 2
    assert {"file", "line", "severity", "issue", "suggestion"} <= set(saved["issues"][0])
    assert "created_at" in saved


def test_no_summary_means_no_summary_comment(post_webhook, pr_payload, mocks):
    mocks.run_review.return_value = (AgentResult(issues=[], summary=""), 0)
    post_webhook(pr_payload)
    mocks.post_summary_comment.assert_not_called()


def test_pipeline_failure_is_logged_not_raised(post_webhook, pr_payload, mocks, capsys):
    mocks.get_pr_files.side_effect = RuntimeError("GitHub is down")
    r = post_webhook(pr_payload)

    assert r.status_code == 200  # GitHub still gets its fast OK
    assert "ERROR while processing PR #7" in capsys.readouterr().out
    mocks.insert_one.assert_not_called()
