"""
Council - Router
Parses @model tags from user messages and routes to the right adapter(s).
"""

import re
from typing import Optional


# Aliases for each model
MODEL_ALIASES = {
    "claude":   ["claude", "c"],
    "gpt":      ["gpt", "chatgpt", "openai", "g"],
    "gemini":   ["gemini", "gem", "google"],
    "all":      ["all", "everyone", "council"],
}

# Reverse lookup: alias -> canonical name
ALIAS_MAP = {}
for canonical, aliases in MODEL_ALIASES.items():
    for alias in aliases:
        ALIAS_MAP[alias.lower()] = canonical


def parse_target(message: str) -> tuple[Optional[str], str]:
    """
    Parse @model tag from message.
    Returns (target_model, cleaned_message).
    target_model is None if no tag found (defaults to last used or ask user).
    """
    pattern = r"^@(\w+)\s*"
    match = re.match(pattern, message.strip(), re.IGNORECASE)

    if match:
        raw_tag = match.group(1).lower()
        canonical = ALIAS_MAP.get(raw_tag)
        cleaned = message[match.end():].strip()
        return canonical, cleaned
    
    return None, message.strip()


def get_available_models(adapters: dict) -> list[str]:
    """Return list of model names that have valid API keys configured."""
    return [name for name, adapter in adapters.items() if adapter.is_configured()]


def resolve_targets(target: Optional[str], adapters: dict, last_target: Optional[str]) -> list[str]:
    """
    Resolve target to a list of model names to call.
    Falls back to last_target, then errors.
    """
    available = get_available_models(adapters)

    if target == "all":
        return available

    if target and target in available:
        return [target]

    if target and target not in adapters:
        return []  # unknown model

    if target and target not in available:
        return []  # model not configured

    # No tag — use last target
    if last_target and last_target in available:
        return [last_target]

    # Default to all configured models
    return available
