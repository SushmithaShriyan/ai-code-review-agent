"""verify_signature: the HMAC-SHA256 check that stops fake webhooks."""

from app.github_client import verify_signature
from tests.conftest import sign


def test_valid_signature_is_accepted():
    body = b'{"hello": "world"}'
    assert verify_signature(body, sign(body)) is True


def test_wrong_secret_is_rejected():
    body = b'{"hello": "world"}'
    assert verify_signature(body, sign(body, secret="other-secret")) is False


def test_tampered_body_is_rejected():
    signature = sign(b'{"amount": 1}')
    assert verify_signature(b'{"amount": 999}', signature) is False


def test_missing_signature_is_rejected():
    assert verify_signature(b"{}", "") is False


def test_rejects_everything_when_no_secret_configured(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "github_webhook_secret", "")
    body = b"{}"
    assert verify_signature(body, sign(body)) is False
