"""The one place where "which AI reads the message?" is decided.

Today the only working provider is the local, rule-based one.  It costs
nothing, needs no API key and always gives the same answer for the same
message, which makes it testable.

This build deliberately contains NO live model adapter.  Writing one that has
never been run against a real account would be untested code pretending to be
an integration.  When you approve a budget for API usage, add a provider class
here that implements `classify()` and returns the same `IntentResult`, then
choose it with AI_PROVIDER in `.env`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from orchestration.intent_router import IntentResult, route


class IntentProvider(Protocol):
    name: str

    def classify(self, message: str) -> IntentResult: ...


class MockIntentProvider:
    """Rule-based classifier used for all local development and testing."""

    name = "mock-rule-based"

    def classify(self, message: str) -> IntentResult:
        return route(message)


class LiveAiNotConfigured(RuntimeError):
    """Raised when a live AI provider is requested but none exists in this build."""


def get_intent_provider(settings: Settings) -> IntentProvider:
    provider = (settings.ai_provider or "mock").strip().lower()
    if provider == "mock" and not settings.enable_live_ai:
        return MockIntentProvider()

    raise LiveAiNotConfigured(
        "Live AI is not available in this build. AI_PROVIDER="
        f"{settings.ai_provider!r}, ENABLE_LIVE_AI={settings.enable_live_ai}. "
        "No paid model has been approved or connected yet, so nothing was called "
        "and no cost was incurred. Set AI_PROVIDER=mock and ENABLE_LIVE_AI=false "
        "in .env to use the free local provider."
    )
