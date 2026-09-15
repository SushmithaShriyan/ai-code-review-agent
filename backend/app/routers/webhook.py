"""
This is the entry point of the whole system: GitHub calls this endpoint
whenever a PR is opened or updated.

IMPORTANT DESIGN NOTE (good interview material):
GitHub requires a webhook response within ~10 seconds, but our review
pipeline (fetch diff -> call LLM -> post comments -> save to DB) takes
longer than that. So we acknowledge the webhook IMMEDIATELY and run the
actual work in a background task. This is a standard pattern for any
webhook handler that does slow work.
"""

from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from app.github_client import verify_signature, get_pr_files, post_review_comment, post_summary_comment
from app.agent import run_review
from app.database import reviews_collection
from app.models import Review

router = APIRouter()


async def process_review(owner: str, repo: str, repo_full_name: str, pr_number: int, pr_title: str, commit_id: str):
    """Runs the whole review pipeline. Called in the background."""
    try:
        # 1. Fetch the diff
        files = await get_pr_files(owner, repo, pr_number)
        print(f"[webhook] Fetched {len(files)} changed file(s) for PR #{pr_number}")

        # 2. Run the AI agent over the diff
        result, latency_ms = await run_review(files)
        print(f"[webhook] Agent found {len(result.issues)} issue(s) in {latency_ms}ms")

        # 3. Post inline comments for each flagged issue
        for issue in result.issues:
            if issue.line is None:
                continue
            comment_body = (
                f"**[{issue.severity.upper()}] {issue.issue}**\n\n"
                f"Suggestion: {issue.suggestion}\n\n"
                f"_— posted by AI Code Review Agent_"
            )
            await post_review_comment(owner, repo, pr_number, commit_id, issue.file, issue.line, comment_body)

        # 4. Post one summary comment
        if result.summary:
            await post_summary_comment(
                owner, repo, pr_number,
                f"### 🤖 AI Review Summary\n\n{result.summary}\n\nFound **{len(result.issues)}** issue(s)."
            )

        # 5. Log everything to MongoDB for the dashboard
        review = Review(
            repo=repo_full_name,
            pr_number=pr_number,
            pr_title=pr_title,
            commit_id=commit_id,
            issues=result.issues,
            summary=result.summary,
            model_used="gemini-3.5-flash-lite",
            latency_ms=latency_ms,
        )
        await reviews_collection.insert_one(review.model_dump())
        print(f"[webhook] Review for PR #{pr_number} saved to database")

    except Exception as e:
        # Background tasks fail silently otherwise - log loudly so we can debug.
        print(f"[webhook] ERROR while processing PR #{pr_number}: {type(e).__name__}: {e}")


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default=""),
):
    body = await request.body()

    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()

    if x_github_event != "pull_request" or payload.get("action") not in ("opened", "synchronize"):
        return {"status": "ignored", "reason": f"event={x_github_event} action={payload.get('action')}"}

    pr = payload["pull_request"]
    repo_full_name = payload["repository"]["full_name"]
    owner, repo = repo_full_name.split("/")

    # Queue the slow work, then return immediately so GitHub doesn't time out.
    background_tasks.add_task(
        process_review,
        owner,
        repo,
        repo_full_name,
        pr["number"],
        pr.get("title", ""),
        pr["head"]["sha"],
    )

    return {"status": "accepted", "pr_number": pr["number"]}