"""Shared fixtures. Nothing here talks to GitHub, Gemini or MongoDB."""

import hashlib
import hmac
import json
import os

# app/agent.py builds its Gemini client when the file is imported, which fails
# without an API key. Set harmless dummy values BEFORE importing the app so the
# tests also work on a clean machine / CI with no .env file.
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

SECRET = "test-secret"


def sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def _test_settings(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", SECRET)
    monkeypatch.setattr(settings, "github_token", "fake-token")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def pr_payload():
    return {
        "action": "opened",
        "pull_request": {"number": 7, "title": "Add login", "head": {"sha": "abc123"}},
        "repository": {"full_name": "someone/some-repo"},
    }


@pytest.fixture
def post_webhook(client):
    """Helper: POST a correctly signed webhook unless told otherwise."""

    def _post(payload, event="pull_request", signature=None):
        body = json.dumps(payload).encode()
        headers = {
            "X-GitHub-Event": event,
            "X-Hub-Signature-256": sign(body) if signature is None else signature,
            "Content-Type": "application/json",
        }
        return client.post("/webhook/github", content=body, headers=headers)

    return _post
