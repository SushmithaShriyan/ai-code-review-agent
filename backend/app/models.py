"""
Data models. These give us:
1. Validation of what the LLM returns (if the LLM's JSON doesn't match
   this shape, Pydantic raises an error we can catch and retry/log).
2. A clear contract for the frontend (the /reviews endpoint returns objects
   shaped exactly like Review below).
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Issue(BaseModel):
    file: str
    line: Optional[int] = None
    severity: str  # "low" | "medium" | "high"
    issue: str
    suggestion: str


class AgentResult(BaseModel):
    """What we ask the LLM to return, enforced via prompt + validation."""
    issues: List[Issue] = Field(default_factory=list)
    summary: str = ""


class Review(BaseModel):
    repo: str
    pr_number: int
    pr_title: str
    commit_id: str
    issues: List[Issue]
    summary: str
    model_used: str
    latency_ms: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewStats(BaseModel):
    total_reviews: int
    total_issues: int
    issues_by_severity: dict
    avg_latency_ms: float
