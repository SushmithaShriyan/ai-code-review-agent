"""
This is the "agent" - the part of the project that's actually AI engineering,
not just CRUD. Keep this file the centerpiece of your README and your
interview explanation.

Design decisions worth remembering for interviews:
1. We force STRUCTURED output (JSON matching AgentResult) instead of letting
   the model ramble in prose. This is what makes it possible to post
   comments programmatically and store results in a queryable schema.
2. We review file-by-file rather than dumping the whole PR into one prompt.
   This keeps prompts small (cheaper, faster) and makes it easy to attribute
   an issue back to a specific file.
3. We measure and store latency + which model was used, because "I built an
   AI feature" is weak; "I built an AI feature and measured its cost/latency
   tradeoffs" is a production-engineering signal.
"""

import json
import time
from openai import AsyncOpenAI
from app.config import settings
from app.models import AgentResult

client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

SYSTEM_PROMPT = """You are a senior software engineer performing a pull request code review.

Review the given diff for exactly these three categories, nothing else:
1. SECURITY - hardcoded secrets/API keys, SQL injection risk, unsafe eval/exec, missing input validation.
2. CODE QUALITY - unclear naming, excessive complexity, missing error handling, dead code.
3. PERFORMANCE - N+1 query patterns, unnecessary loops/recomputation, inefficient data structures.

Rules:
- Only flag real issues you can point to a specific line for. Do not invent line numbers.
- Be concise: one sentence for the issue, one sentence for the suggested fix.
- If the diff has no real issues, return an empty issues list. Do not invent issues to seem useful.
- Respond with ONLY valid JSON matching this schema, no markdown fences, no extra text:

{
  "issues": [
    {"file": "<filename>", "line": <int>, "severity": "low|medium|high", "issue": "<string>", "suggestion": "<string>"}
  ],
  "summary": "<one paragraph overall summary>"
}
"""


def _build_diff_context(files: list[dict]) -> str:
    """Turns GitHub's file list into a compact text block the LLM can read."""
    parts = []
    for f in files:
        patch = f.get("patch")
        if not patch:
            continue  # binary files, or files GitHub didn't generate a patch for
        parts.append(f"### File: {f['filename']}\n{patch}\n")
    return "\n".join(parts)


async def run_review(files: list[dict]) -> tuple[AgentResult, int]:
    """
    Runs the review agent over a PR's changed files.
    Returns (result, latency_ms).
    """
    diff_context = _build_diff_context(files)

    if not diff_context.strip():
        return AgentResult(issues=[], summary="No reviewable text changes found."), 0

    start = time.perf_counter()

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": diff_context},
        ],
        temperature=0,  # deterministic-ish output for a review tool
        response_format={"type": "json_object"},
    )

    latency_ms = int((time.perf_counter() - start) * 1000)
    raw = response.choices[0].message.content

    try:
        parsed = json.loads(raw)
        result = AgentResult(**parsed)
    except Exception as e:
        # If the model returns malformed JSON, fail soft instead of crashing
        # the whole webhook handler.
        print(f"[agent] Failed to parse LLM output: {e}\nRaw: {raw}")
        result = AgentResult(issues=[], summary="Agent failed to produce a valid review.")

    return result, latency_ms
