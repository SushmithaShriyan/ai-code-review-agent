"""The LLM agent: prompt building, structured output and fail-soft behaviour.
The Gemini call is mocked, so these tests are free and instant."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.agent as agent
from app.agent import _build_diff_context, run_review


def fake_llm_reply(content: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.fixture
def llm(monkeypatch):
    create = AsyncMock()
    monkeypatch.setattr(agent.client.chat.completions, "create", create)
    return create


# ---------- _build_diff_context ----------

def test_diff_context_includes_filename_and_patch():
    text = _build_diff_context([{"filename": "a.py", "patch": "+x = 1"}])
    assert "### File: a.py" in text and "+x = 1" in text


def test_diff_context_skips_files_without_patch():
    text = _build_diff_context([{"filename": "logo.png"}, {"filename": "a.py", "patch": "+x"}])
    assert "logo.png" not in text and "a.py" in text


# ---------- run_review ----------

async def test_valid_json_is_parsed_into_issues(llm):
    llm.return_value = fake_llm_reply(json.dumps({
        "issues": [{"file": "config.py", "line": 1, "severity": "high",
                    "issue": "Hardcoded password", "suggestion": "Use an env var"}],
        "summary": "Found a secret.",
    }))
    result, latency = await run_review([{"filename": "config.py", "patch": '+DB_PASSWORD = "admin123"'}])

    assert len(result.issues) == 1
    assert result.issues[0].severity == "high"
    assert result.summary == "Found a secret."
    assert latency >= 0


async def test_clean_diff_returns_no_issues(llm):
    llm.return_value = fake_llm_reply(json.dumps({"issues": [], "summary": "Looks good."}))
    result, _ = await run_review([{"filename": "a.py", "patch": "+x = 1"}])
    assert result.issues == []


async def test_diff_is_sent_to_the_model_with_json_mode(llm):
    llm.return_value = fake_llm_reply('{"issues": [], "summary": ""}')
    await run_review([{"filename": "a.py", "patch": "+x = 1"}])

    kwargs = llm.await_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["temperature"] == 0
    assert kwargs["messages"][0]["role"] == "system"
    assert "+x = 1" in kwargs["messages"][1]["content"]


async def test_invalid_json_fails_soft(llm):
    llm.return_value = fake_llm_reply("Sure! Here is my review: looks fine")
    result, _ = await run_review([{"filename": "a.py", "patch": "+x"}])

    assert result.issues == []
    assert result.summary == "Agent failed to produce a valid review."


async def test_json_with_wrong_shape_fails_soft(llm):
    # severity / suggestion missing -> pydantic validation error -> safe result
    llm.return_value = fake_llm_reply(json.dumps({"issues": [{"file": "a.py"}], "summary": "x"}))
    result, _ = await run_review([{"filename": "a.py", "patch": "+x"}])

    assert result.issues == []
    assert "failed" in result.summary.lower()


async def test_no_text_changes_skips_the_llm_call(llm):
    result, latency = await run_review([{"filename": "image.png"}])

    llm.assert_not_called()
    assert result.issues == []
    assert latency == 0
