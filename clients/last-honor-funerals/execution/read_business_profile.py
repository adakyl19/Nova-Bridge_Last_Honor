"""Read the approved business information from data/business_profile.json.

This is the ONLY place business facts come from.  The receptionist can never
invent an address, a price or an opening time: it asks this module, and this
module refuses to hand over anything the owner has not marked as "verified".

To update business information you edit the JSON file (or run this module to
see what is still missing).  No code changes are needed.

Run it to see the current status:
    cd clients/last-honor-funerals
    python execution/read_business_profile.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

if __package__ in (None, ""):  # allow "python execution/read_business_profile.py"
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import load_settings

_VALID_STATUSES = {"verified", "unverified"}


@dataclass(frozen=True)
class Fact:
    """One piece of business information, with its approval state."""

    key: str
    status: str
    value: Any
    placeholder: str
    description: str = ""

    @property
    def is_available(self) -> bool:
        """True only when the owner verified it AND a real value is present.

        A field marked "verified" but still holding its placeholder is treated
        as unavailable, so a half-finished edit can never leak to a customer.
        """
        if self.status != "verified":
            return False
        if self.value in (None, "", [], {}):
            return False
        return str(self.value).strip() != self.placeholder


@dataclass(frozen=True)
class BusinessProfile:
    name: str
    country: str
    approved: bool
    facts: Mapping[str, Fact]
    source_path: Path

    def fact(self, key: str) -> Fact:
        existing = self.facts.get(key)
        if existing is not None:
            return existing
        return Fact(key=key, status="unverified", value=None, placeholder=f"[{key.upper()}]")

    def is_available(self, key: str) -> bool:
        return self.fact(key).is_available

    def value(self, key: str) -> Any:
        """The verified value, or None. Never returns a placeholder."""
        fact = self.fact(key)
        return fact.value if fact.is_available else None

    def missing(self) -> list[Fact]:
        return [fact for fact in self.facts.values() if not fact.is_available]


class BusinessProfileError(RuntimeError):
    """Raised when the business profile file is missing or malformed."""


def load_profile(path: Path | str | None = None) -> BusinessProfile:
    profile_path = Path(path) if path else load_settings().business_profile_path
    if not profile_path.is_file():
        raise BusinessProfileError(
            f"Business profile not found at {profile_path}. "
            "Copy data/business_profile.json back into place."
        )
    try:
        raw = json.loads(profile_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BusinessProfileError(f"{profile_path} is not valid JSON: {exc}") from exc

    meta = raw.get("meta", {})
    facts: dict[str, Fact] = {}
    for key, entry in raw.get("facts", {}).items():
        status = str(entry.get("status", "unverified")).strip().lower()
        if status not in _VALID_STATUSES:
            status = "unverified"
        facts[key] = Fact(
            key=key,
            status=status,
            value=entry.get("value"),
            placeholder=str(entry.get("placeholder", f"[{key.upper()}]")),
            description=str(entry.get("description", "")),
        )

    return BusinessProfile(
        name=str(meta.get("business_name", "Last Honor Funerals")),
        country=str(meta.get("country", "South Africa")),
        approved=bool(meta.get("profile_approved", False)),
        facts=facts,
        source_path=profile_path,
    )


def main() -> int:
    profile = load_profile()
    print(f"Business profile: {profile.source_path}")
    print(f"Business name:    {profile.name} ({profile.country})")
    print(f"Approved by owner: {'yes' if profile.approved else 'NO - placeholders in use'}")
    print("")
    print(f"{'FIELD':<24} {'STATUS':<12} VALUE / PLACEHOLDER")
    print("-" * 78)
    for fact in profile.facts.values():
        shown = fact.value if fact.is_available else fact.placeholder
        print(f"{fact.key:<24} {fact.status:<12} {shown}")
    missing = profile.missing()
    print("-" * 78)
    print(f"{len(missing)} field(s) still need verified information.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
