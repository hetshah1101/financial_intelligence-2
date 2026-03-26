# app/services/ai_service.py - AI abstraction layer for financial insights

import json
import logging
from typing import Optional

import requests

from app.config import config
from app.db.database import get_connection

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a financial analyst AI specializing in personal finance.

Your job:
- Interpret structured financial data
- Identify patterns, anomalies, inefficiencies
- Provide clear, actionable recommendations

STRICT RULES:
- Follow the output format EXACTLY
- Do NOT add extra explanations
- Do NOT repeat raw numbers unnecessarily
- Avoid generic advice — be specific to the data
- Use ₹ currency
- Maximum 6 insights total
- Each insight must follow: Observation → Implication → Action

OUTPUT FORMAT (use exactly these headers):

### Key Insights
1. ...
2. ...

### Anomalies & Risks
- ...

### Optimization Opportunities
- ...

### Recommended Actions
1. ...
2. ...
"""


def build_user_prompt(analytics: dict) -> str:
    return (
        "Analyze this financial data and generate insights:\n\n"
        f"```json\n{json.dumps(analytics, indent=2, ensure_ascii=False)}\n```\n\n"
        "Generate insights following the required format. Be concise and specific."
    )


def call_ollama(prompt: str, system: str) -> str:
    """Call local Ollama model."""
    payload = {
        "model":  config.ollama.model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 1024,
        },
    }
    response = requests.post(
        f"{config.ollama.host}/api/generate",
        json=payload,
        timeout=config.ollama.timeout,
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def call_openai_compatible(prompt: str, system: str) -> str:
    """Call OpenAI-compatible API as fallback."""
    if not config.openai.api_key:
        raise RuntimeError("OpenAI API key not configured")

    headers = {
        "Authorization": f"Bearer {config.openai.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.openai.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens":  1024,
    }
    response = requests.post(
        f"{config.openai.base_url}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def generate_insights(analytics: dict) -> str:
    """
    Route to Ollama (primary) or OpenAI (fallback) based on config.
    AI receives only pre-computed structured JSON — it never performs calculations.
    """
    user_prompt = build_user_prompt(analytics)
    provider    = config.app.ai_provider

    if provider in ("ollama", "auto"):
        try:
            logger.info("Calling Ollama for insights generation")
            result = call_ollama(user_prompt, SYSTEM_PROMPT)
            logger.info("Ollama response received")
            return result
        except Exception as e:
            logger.warning(f"Ollama failed: {e}")
            if provider == "ollama":
                raise RuntimeError(f"Ollama unavailable: {e}") from e
            logger.info("Falling back to OpenAI-compatible API")

    if provider in ("openai", "auto"):
        try:
            logger.info("Calling OpenAI-compatible API")
            result = call_openai_compatible(user_prompt, SYSTEM_PROMPT)
            logger.info("OpenAI response received")
            return result
        except Exception as e:
            logger.error(f"OpenAI fallback also failed: {e}")
            raise RuntimeError(f"All AI providers failed. Last error: {e}") from e

    raise ValueError(f"Unknown AI provider: {provider}")


def generate_and_cache_insights(month: str, analytics: dict) -> str:
    """Generate insights and persist to insights_cache table."""
    try:
        content = generate_insights(analytics)
    except Exception as e:
        content = f"⚠️ AI insights unavailable: {e}\n\nRaw summary available in dashboard."
        logger.error(f"Insight generation failed for {month}: {e}")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO insights_cache (month, insight_type, content)
            VALUES (?, 'full_analysis', ?)
            ON CONFLICT(month, insight_type) DO UPDATE SET
                content    = excluded.content,
                created_at = datetime('now')
            """,
            (month, content),
        )

    return content


def get_cached_insights(month: str) -> Optional[str]:
    """Retrieve cached insights for a month, or None if not yet generated."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT content FROM insights_cache
            WHERE month = ? AND insight_type = 'full_analysis'
            """,
            (month,),
        ).fetchone()
        return row["content"] if row else None
