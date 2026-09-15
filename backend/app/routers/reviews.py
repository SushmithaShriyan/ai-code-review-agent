"""
Read-only API for the dashboard. Kept separate from the webhook router since
one is triggered by GitHub, the other by the frontend - different callers,
different failure modes, different auth story later if you add one.
"""

from fastapi import APIRouter
from app.database import reviews_collection

router = APIRouter()


@router.get("/reviews")
async def list_reviews(limit: int = 20):
    cursor = reviews_collection.find().sort("created_at", -1).limit(limit)
    reviews = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        reviews.append(doc)
    return reviews


@router.get("/reviews/stats")
async def get_stats():
    reviews = [doc async for doc in reviews_collection.find()]

    total_reviews = len(reviews)
    all_issues = [issue for r in reviews for issue in r.get("issues", [])]
    total_issues = len(all_issues)

    by_severity = {"low": 0, "medium": 0, "high": 0}
    for issue in all_issues:
        sev = issue.get("severity", "low")
        by_severity[sev] = by_severity.get(sev, 0) + 1

    avg_latency = (
        sum(r.get("latency_ms", 0) for r in reviews) / total_reviews
        if total_reviews else 0
    )

    return {
        "total_reviews": total_reviews,
        "total_issues": total_issues,
        "issues_by_severity": by_severity,
        "avg_latency_ms": round(avg_latency, 1),
    }
