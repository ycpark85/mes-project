from __future__ import annotations

from dataclasses import dataclass


MAX_USER_AGENT_LENGTH = 2000


@dataclass(frozen=True)
class NormalizedUserAgent:
    value: str | None
    truncated: bool


def normalize_user_agent(value: str | None) -> NormalizedUserAgent:
    if not value:
        return NormalizedUserAgent(value=None, truncated=False)

    truncated = len(value) > MAX_USER_AGENT_LENGTH
    sample = value[: MAX_USER_AGENT_LENGTH + 1]
    cleaned = "".join(
        character if character.isprintable() else " "
        for character in sample
    ).strip()

    if len(cleaned) > MAX_USER_AGENT_LENGTH:
        cleaned = cleaned[:MAX_USER_AGENT_LENGTH]
        truncated = True

    return NormalizedUserAgent(
        value=cleaned or None,
        truncated=truncated,
    )
