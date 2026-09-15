from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import webhook, reviews
from app.config import settings

app = FastAPI(
    title="AI Code Review Agent",
    description="An AI agent that reviews GitHub pull requests and posts inline comments.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router, tags=["webhook"])
app.include_router(reviews.router, tags=["reviews"])


@app.get("/")
async def health_check():
    return {"status": "ok", "service": "ai-code-review-agent"}
