from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta

import requests
from sqlalchemy.orm import Session

from backend import models
from backend.services.analytics import build_user_context

logger = logging.getLogger(__name__)

HF_API_URL = os.getenv(
    "HF_API_URL",
    "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
)
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")

# Fallback rule-based recommendations keyed by pattern
_FALLBACK_TIPS = {
    "low_sessions": (
        "You only completed a few sessions this week. Even 10 minutes of gentle "
        "Ba Duan Jin each morning can help build consistency and improve energy flow."
    ),
    "low_accuracy": (
        "Your posture accuracy has some room to grow. Focus on slow, deliberate movements "
        "rather than speed — quality over repetition is the Ba Duan Jin principle."
    ),
    "high_stress": (
        "Your stress level appears elevated. The 2nd and 6th movements of Ba Duan Jin "
        "specifically target tension in the shoulders and chest — prioritise those today."
    ),
    "poor_sleep": (
        "Sleep quality affects recovery. Try a short 5-minute Ba Duan Jin breathing "
        "sequence before bed: slow the breath to 4 counts in, 6 counts out."
    ),
    "default": (
        "Keep up your practice. Aim for 3–5 sessions per week and pay attention to "
        "shoulder alignment in movements 1, 3, and 5 to maximise benefit."
    ),
}


def _build_prompt(ctx: dict) -> str:
    sessions = ctx["sessions_this_week"]
    accuracy = ctx["avg_accuracy_pct"]
    minutes = ctx["total_practice_minutes"]
    issues = ", ".join(ctx["low_accuracy_movements"]) or "none"
    stress = ctx["stress_level"] or "not reported"
    sleep = ctx["sleep_quality"] or "not reported"
    age = ctx["age"] or "not specified"

    return (
        f"<s>[INST] You are a digital wellness assistant specialising in Ba Duan Jin "
        f"(Eight Pieces of Brocade) qigong rehabilitation. "
        f"Write a warm, practical daily recommendation in 3–4 sentences.\n\n"
        f"User profile:\n"
        f"- Age: {age}\n"
        f"- Sessions this week: {sessions}\n"
        f"- Average posture accuracy: {accuracy}%\n"
        f"- Total practice time this week: {minutes} minutes\n"
        f"- Movements needing improvement: {issues}\n"
        f"- Self-reported stress level: {stress}/5\n"
        f"- Self-reported sleep quality: {sleep}/5\n\n"
        f"Give a specific, actionable recommendation for today's practice. "
        f"Do not mention scores or numbers — speak naturally and encouragingly. [/INST]"
    )


def _fallback_recommendation(ctx: dict) -> str:
    if ctx["sessions_this_week"] <= 1:
        return _FALLBACK_TIPS["low_sessions"]
    if ctx["avg_accuracy_pct"] < 65:
        return _FALLBACK_TIPS["low_accuracy"]
    if ctx["stress_level"] and ctx["stress_level"] >= 4:
        return _FALLBACK_TIPS["high_stress"]
    if ctx["sleep_quality"] and ctx["sleep_quality"] <= 2:
        return _FALLBACK_TIPS["poor_sleep"]
    return _FALLBACK_TIPS["default"]


def generate_recommendation(db: Session, user: models.User) -> str:
    ctx = build_user_context(db, user)

    if not HF_API_TOKEN:
        logger.warning("HF_API_TOKEN not set — using rule-based fallback recommendation.")
        return _fallback_recommendation(ctx)

    prompt = _build_prompt(ctx)
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 180,
            "temperature": 0.7,
            "do_sample": True,
            "return_full_text": False,
        },
    }

    try:
        resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            text: str = data[0].get("generated_text", "").strip()
            # Strip any partial sentence at end
            for end in (".", "!", "?"):
                idx = text.rfind(end)
                if idx != -1 and idx > len(text) // 2:
                    text = text[: idx + 1]
                    break
            if text:
                return text
    except Exception as exc:
        logger.error("HuggingFace API error: %s — using fallback.", exc)

    return _fallback_recommendation(ctx)
