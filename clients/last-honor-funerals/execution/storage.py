"""Shared storage helpers for the EXECUTION layer.

Every execution script writes append-only JSON Lines files into one local data
folder.  Append-only means a bug can add a bad line but can never wipe existing
history - important for a system that records people's enquiries.

Files created at runtime (all inside `data/runtime/` by default):
    conversation_log.jsonl    every inbound and outbound message
    enquiries.jsonl           one summary record per conversation turn
    callback_requests.jsonl   customer callback requests
    escalations.jsonl         matters handed to a human
    staff_notifications.jsonl the local "staff inbox" (simulated alerts)
    outbox.jsonl              replies the file transport "sent"
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ValidationError(ValueError):
    """Raised when customer-supplied data is missing, too long or malformed."""


def utc_now() -> str:
    """Current UTC time as an ISO-8601 string, e.g. 2026-11-24T09:15:00Z."""
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def new_record_id(prefix: str) -> str:
    """Human-readable unique id, e.g. CB-20261124-3F9A1C."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def clean_text(value: Any, *, field: str, max_length: int = 2000) -> str:
    """Trim and collapse whitespace, and reject empty or oversized values.

    We use this on everything a customer sends before it reaches a file.
    """
    if value is None:
        raise ValidationError(f"{field} is required")
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text:
        raise ValidationError(f"{field} may not be empty")
    if len(text) > max_length:
        raise ValidationError(f"{field} is longer than {max_length} characters")
    return text


_SA_DIGITS = re.compile(r"^0[1-8]\d{8}$")
_INTL_DIGITS = re.compile(r"^\d{9,15}$")


def normalise_phone(raw: str) -> str | None:
    """Turn a typed phone number into a consistent form, or return None.

    South African numbers are the priority (082 123 4567 -> +27821234567) but
    international numbers are accepted in +... form.
    """
    if not raw:
        return None
    had_plus = raw.strip().startswith("+")
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None

    if digits.startswith("0027"):
        digits = digits[2:]
    if digits.startswith("27") and len(digits) == 11:
        digits = "0" + digits[2:]
    if _SA_DIGITS.match(digits):
        return "+27" + digits[1:]
    if had_plus and _INTL_DIGITS.match(digits):
        return "+" + digits
    return None


def format_phone_for_display(phone: str | None) -> str:
    """+27821234567 -> 082 123 4567 (South African), otherwise unchanged."""
    if not phone:
        return ""
    if phone.startswith("+27") and len(phone) == 12:
        local = "0" + phone[3:]
        return f"{local[:3]} {local[3:6]} {local[6:]}"
    return phone


# 13-digit South African ID numbers and long bank-card-like numbers.
_SENSITIVE_NUMBER = re.compile(r"\b\d{13,19}\b")
_SENSITIVE_LABEL = re.compile(
    r"\b(id|identity|passport|bank|account)\s*(number|no\.?|nr)?\b\s*[:#]?\s*([A-Za-z0-9-]{5,})",
    re.IGNORECASE,
)


def redact_sensitive(text: str) -> tuple[str, bool]:
    """Remove ID / banking details before text is written to a log file.

    Returns the cleaned text and whether anything was redacted.  The customer
    is still told (by the response builder) not to send such details.
    """
    if not text:
        return "", False
    cleaned, count = _SENSITIVE_NUMBER.subn("[redacted-number]", text)
    cleaned, label_count = _SENSITIVE_LABEL.subn(
        lambda m: f"{m.group(1)} {m.group(2) or 'number'} [redacted]", cleaned
    )
    return cleaned, bool(count or label_count)


def contains_sensitive_details(text: str) -> bool:
    """True if a message looks like it contains an ID, passport or bank detail."""
    return bool(_SENSITIVE_NUMBER.search(text) or _SENSITIVE_LABEL.search(text))


class Store:
    """Append-only JSONL storage rooted in one folder."""

    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, kind: str) -> Path:
        if not re.fullmatch(r"[a-z_]+", kind):
            raise ValidationError(f"invalid log name: {kind!r}")
        return self.data_dir / f"{kind}.jsonl"

    def append(
        self,
        kind: str,
        record: dict[str, Any],
        *,
        record_id: str | None = None,
    ) -> dict[str, Any]:
        """Add one record to a log file and return it (with id and timestamp)."""
        stored = dict(record)
        stored.setdefault("recorded_at", utc_now())
        stored["record_id"] = record_id or stored.get("record_id") or new_record_id(
            kind[:3].upper()
        )
        with self.path_for(kind).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(stored, ensure_ascii=False, default=str) + "\n")
        return stored

    def read(self, kind: str) -> list[dict[str, Any]]:
        """Read a log file. Unreadable lines are skipped rather than crashing."""
        path = self.path_for(kind)
        if not path.is_file():
            return []
        records: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records
