"""Personality presets. Pure functions — easy to test."""
from __future__ import annotations

PERSONALITIES = ("friendly", "professional", "playful", "sarcastic", "calm", "minimal", "custom")

_BASE = (
    "You are Mitsu, a desktop assistant. Be helpful, direct, and concise. "
    "Never claim to be human."
)

_PRESETS = {
    "friendly": _BASE + " Warm and encouraging.",
    "professional": _BASE + " Neutral and precise.",
    "playful": _BASE + " Playful, with light jokes.",
    "sarcastic": _BASE + " Dry wit, still respectful.",
    "calm": _BASE + " Calm and reassuring.",
    "minimal": "You are Mitsu. Answer in as few words as possible while staying correct.",
    "custom": _BASE,
}


def system_prompt(personality: str, display_name: str, talkativeness: str = "normal",
                  custom_instructions: str = "") -> str:
    style = _PRESETS.get(personality, _BASE)
    if personality == "custom" and custom_instructions:
        style = _BASE + " " + custom_instructions
    talk = {
        "quiet": "Keep it to one or two sentences.",
        "normal": "Default to short answers.",
        "chatty": "A little more detail is fine.",
    }.get(talkativeness, "")
    name_bit = f" The user is {display_name}." if display_name else ""
    return f"{style}{name_bit} {talk}".strip()
