"""GitHub REST calls, run against httpx's in-memory MockTransport (no network)."""

import json

import httpx
import pytest

import app.github_client as gh


@pytest.fixture
def github(monkeypatch):
    """Route every httpx.AsyncClient() in github_client to a fake handler."""
    calls = []
    state = {"status": 200, "body": {}}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(state["status"], json=state["body"])

    real_client = httpx.AsyncClient
    monkeypatch.setattr(gh.httpx, "AsyncClient", lambda *a, **k: real_client(transport=httpx.MockTransport(handler)))
    return calls, state


async def test_get_pr_files_returns_json_and_sends_auth(github):
    calls, state = github
    state["body"] = [{"filename": "a.py", "patch": "+x"}]

    files = await gh.get_pr_files("someone", "some-repo", 7)

    assert files == [{"filename": "a.py", "patch": "+x"}]
    assert calls[0].url.path == "/repos/someone/some-repo/pulls/7/files"
    assert calls[0].headers["Authorization"] == "Bearer fake-token"


async def test_get_pr_files_raises_on_http_error(github):
    _, state = github
    state["status"] = 404
    with pytest.raises(httpx.HTTPStatusError):
        await gh.get_pr_files("someone", "some-repo", 7)


async def test_inline_comment_payload_targets_exact_line(github):
    calls, _ = github
    await gh.post_review_comment("someone", "some-repo", 7, "abc123", "a.py", 12, "Fix this")

    body = json.loads(calls[0].content)
    assert calls[0].url.path == "/repos/someone/some-repo/pulls/7/comments"
    assert body == {"body": "Fix this", "commit_id": "abc123", "path": "a.py", "line": 12, "side": "RIGHT"}


async def test_failed_inline_comment_does_not_raise(github, capsys):
    _, state = github
    state["status"] = 422  # e.g. line is not part of the diff
    resp = await gh.post_review_comment("o", "r", 1, "sha", "a.py", 999, "x")

    assert resp.status_code == 422
    assert "Failed to post comment" in capsys.readouterr().out


async def test_summary_comment_uses_issues_endpoint(github):
    calls, _ = github
    await gh.post_summary_comment("someone", "some-repo", 7, "All done")

    assert calls[0].url.path == "/repos/someone/some-repo/issues/7/comments"
    assert json.loads(calls[0].content) == {"body": "All done"}


async def test_get_pr_returns_pull_request_json(github):
    calls, state = github
    state["body"] = {"number": 7, "title": "Add login"}

    pr = await gh.get_pr("someone", "some-repo", 7)

    assert pr["title"] == "Add login"
    assert calls[0].url.path == "/repos/someone/some-repo/pulls/7"
