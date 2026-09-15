"""
All GitHub REST API interaction lives here, kept separate from the webhook
route and the agent logic. This separation is on purpose: if you ever swap
GitHub for GitLab/Bitbucket, this is the only file that changes.
"""

import hashlib
import hmac
import httpx
from app.config import settings

GITHUB_API = "https://api.github.com"


def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    GitHub signs every webhook payload with your webhook secret (HMAC-SHA256).
    We recompute the signature ourselves and compare. This stops anyone who
    isn't GitHub from POSTing fake PR events at your endpoint.
    """
    if not signature_header or not settings.github_webhook_secret:
        return False

    hash_object = hmac.new(
        settings.github_webhook_secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)


def _headers():
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def get_pr_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    """
    Returns the list of changed files in a PR, each with a `patch` field
    (the unified diff text) that we feed to the LLM.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def get_pr(owner: str, repo: str, pr_number: int) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def post_review_comment(
    owner: str, repo: str, pr_number: int, commit_id: str, path: str, line: int, body: str
):
    """
    Posts a single inline comment on a specific line of a specific file in
    the PR - this is what makes the review show up exactly like a human
    reviewer's comment on GitHub.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
    payload = {
        "body": body,
        "commit_id": commit_id,
        "path": path,
        "line": line,
        "side": "RIGHT",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=_headers(), json=payload)
        # Don't raise on failure - a single bad line number shouldn't kill the
        # whole review. Log and move on to the next comment instead.
        if resp.status_code >= 400:
            print(f"[github_client] Failed to post comment on {path}:{line} -> {resp.text}")
        return resp


async def post_summary_comment(owner: str, repo: str, pr_number: int, body: str):
    """Posts one top-level PR comment summarizing the whole review."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=_headers(), json={"body": body})
        return resp
