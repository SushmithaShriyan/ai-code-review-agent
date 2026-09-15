"""
Quick manual test for the AI review agent - no GitHub or webhook needed.
Run this from the backend folder with the venv active:
    python test_agent.py
"""

import asyncio
from app.agent import run_review

# A fake "PR file" with an obvious issue (hardcoded password) to see if
# the agent actually catches it.
fake_files = [
    {
        "filename": "config.py",
        "patch": (
            "@@ -1,3 +1,5 @@\n"
            "+DB_PASSWORD = \"admin123\"\n"
            "+\n"
            "+def get_user(id):\n"
            "+    query = \"SELECT * FROM users WHERE id = \" + id\n"
            "+    return db.execute(query)\n"
        ),
    }
]


async def main():
    result, latency_ms = await run_review(fake_files)
    print(f"\nLatency: {latency_ms}ms")
    print(f"Summary: {result.summary}\n")
    print(f"Found {len(result.issues)} issue(s):")
    for issue in result.issues:
        print(f"  [{issue.severity.upper()}] {issue.file}:{issue.line} - {issue.issue}")
        print(f"    Suggestion: {issue.suggestion}")


if __name__ == "__main__":
    asyncio.run(main())