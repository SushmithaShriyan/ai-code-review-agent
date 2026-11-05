"""Dashboard endpoints (/reviews and /reviews/stats) with a fake MongoDB collection."""

import pytest

import app.routers.reviews as reviews_router


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)
        self.sort_args = None
        self.limit_value = None

    def sort(self, *args):
        self.sort_args = args
        return self

    def limit(self, n):
        self.limit_value = n
        self.docs = self.docs[:n]
        return self

    def __aiter__(self):
        async def gen():
            for d in self.docs:
                yield d
        return gen()


class FakeCollection:
    def __init__(self, docs):
        self.docs = docs
        self.last_cursor = None

    def find(self):
        self.last_cursor = FakeCursor(self.docs)
        return self.last_cursor


def use_docs(monkeypatch, docs):
    coll = FakeCollection(docs)
    monkeypatch.setattr(reviews_router, "reviews_collection", coll)
    return coll


def test_health_check(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "ai-code-review-agent"}


def test_list_reviews_newest_first_and_id_is_string(client, monkeypatch):
    coll = use_docs(monkeypatch, [{"_id": object(), "repo": "a/b"}, {"_id": object(), "repo": "c/d"}])

    r = client.get("/reviews?limit=5")

    assert r.status_code == 200
    assert [d["repo"] for d in r.json()] == ["a/b", "c/d"]
    assert all(isinstance(d["_id"], str) for d in r.json())
    assert coll.last_cursor.sort_args == ("created_at", -1)
    assert coll.last_cursor.limit_value == 5


def test_stats_with_no_reviews_is_all_zero(client, monkeypatch):
    use_docs(monkeypatch, [])
    assert client.get("/reviews/stats").json() == {
        "total_reviews": 0,
        "total_issues": 0,
        "issues_by_severity": {"low": 0, "medium": 0, "high": 0},
        "avg_latency_ms": 0,
    }


def test_stats_counts_issues_by_severity_and_averages_latency(client, monkeypatch):
    use_docs(monkeypatch, [
        {"issues": [{"severity": "high"}, {"severity": "low"}], "latency_ms": 1000},
        {"issues": [{"severity": "high"}], "latency_ms": 2000},
        {"issues": [], "latency_ms": 3000},
    ])
    data = client.get("/reviews/stats").json()

    assert data["total_reviews"] == 3
    assert data["total_issues"] == 3
    assert data["issues_by_severity"] == {"low": 1, "medium": 0, "high": 2}
    assert data["avg_latency_ms"] == 2000.0
