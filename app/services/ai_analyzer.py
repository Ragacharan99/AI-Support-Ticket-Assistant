"""AI-backed ticket classification and response drafting."""

import json
import re
from typing import Literal

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI
from pydantic import BaseModel, ValidationError

from ..config import API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL


class AnalysisError(Exception):
    """Raised when the AI provider cannot produce a usable ticket analysis."""


class AnalysisResult(BaseModel):
    """Structured result returned by the AI analysis workflow."""

    category: Literal["billing", "technical", "account", "feature_request", "other"]
    urgency: Literal["low", "medium", "high", "critical"]
    summary: str
    suggested_reply: str


PROMPT = """Analyze this customer support ticket. Return JSON only, with no markdown or explanation.
Use exactly these fields:
{{
  "category": "billing|technical|account|feature_request|other",
  "urgency": "low|medium|high|critical",
  "summary": "one or two sentence summary",
  "suggested_reply": "helpful customer-facing reply"
}}

Ticket subject: {subject}
Ticket body: {body}
"""


def _extract_json(content: str) -> dict:
    """Remove optional Markdown fencing and decode the first JSON object."""
    unfenced = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", content, flags=re.IGNORECASE)
    start = unfenced.find("{")
    if start == -1:
        raise ValueError("AI response did not contain a JSON object")

    payload, _ = json.JSONDecoder().raw_decode(unfenced[start:])
    if not isinstance(payload, dict):
        raise ValueError("AI response JSON must be an object")
    return payload


def _request_analysis(subject: str, body: str) -> str:
    """Call NVIDIA's OpenAI-compatible chat endpoint once."""
    if not API_KEY:
        raise AnalysisError("AI analysis is unavailable: API_KEY is not configured")
    if not NVIDIA_MODEL:
        raise AnalysisError("AI analysis is unavailable: NVIDIA_MODEL is not configured")

    client = OpenAI(api_key=API_KEY, base_url=NVIDIA_BASE_URL, timeout=30, max_retries=0)
    try:
        completion = client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[{"role": "user", "content": PROMPT.format(subject=subject, body=body)}],
            max_tokens=2000,
        )
        content = completion.choices[0].message.content if completion.choices else None
    except (APITimeoutError, APIConnectionError, APIError) as exc:
        raise AnalysisError(f"AI provider request failed: {exc}") from exc

    if not content or not content.strip():
        raise AnalysisError("AI provider returned an empty response; the model may have run out of tokens")
    return content


def analyze_ticket(subject: str, body: str) -> AnalysisResult:
    """Analyze a ticket, retrying once only for malformed model output."""
    last_error: Exception | None = None
    for _ in range(2):
        content = _request_analysis(subject, body)
        try:
            return AnalysisResult.model_validate(_extract_json(content))
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = exc

    raise AnalysisError(f"AI provider returned invalid analysis JSON after two attempts: {last_error}")
