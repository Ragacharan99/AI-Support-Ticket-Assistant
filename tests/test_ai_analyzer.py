"""Unit tests for AI response extraction and retry behavior without network calls."""

import pytest

from app.services import ai_analyzer


def test_extract_json_handles_fenced_json():
    assert ai_analyzer._extract_json("```json\n{\"category\": \"billing\"}\n```") == {"category": "billing"}


def test_extract_json_handles_surrounding_text():
    content = 'Here is the result: {"category": "account"} Thanks.'
    assert ai_analyzer._extract_json(content) == {"category": "account"}


def test_extract_json_raises_when_no_json_exists():
    with pytest.raises(ValueError, match="did not contain"):
        ai_analyzer._extract_json("No structured response")


def test_analyze_retries_once_after_bad_json(monkeypatch):
    responses = iter(
        [
            "not JSON",
            '{"category":"technical","urgency":"medium","summary":"Login error.","suggested_reply":"Hello, we are investigating."}',
        ]
    )
    monkeypatch.setattr(ai_analyzer, "_request_analysis", lambda subject, body: next(responses))

    result = ai_analyzer.analyze_ticket("Login error", "I cannot sign in")

    assert result.category == "technical"
    assert result.urgency == "medium"


def test_analyze_fails_after_two_bad_responses(monkeypatch):
    monkeypatch.setattr(ai_analyzer, "_request_analysis", lambda subject, body: "not JSON")

    with pytest.raises(ai_analyzer.AnalysisError, match="after two attempts"):
        ai_analyzer.analyze_ticket("Question", "Please help")


def test_empty_model_content_raises_analysis_error(monkeypatch):
    monkeypatch.setattr(ai_analyzer, "_request_analysis", lambda subject, body: "")

    with pytest.raises(ai_analyzer.AnalysisError):
        ai_analyzer.analyze_ticket("Question", "Please help")
