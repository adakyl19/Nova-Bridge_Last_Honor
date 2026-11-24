"""Create a validated callback request for the funeral parlour's team.

A callback request is only recorded when it has a real name and a phone number
we can dial.  Invalid input raises `ValidationError` instead of writing a
half-useful record that staff cannot action.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.storage import (
    Store,
    ValidationError,
    clean_text,
    new_record_id,
    normalise_phone,
    redact_sensitive,
)


def create_callback_request(
    store: Store,
    *,
    conversation_id: str,
    customer_name: str | None,
    customer_phone: str | None,
    reason: str,
    urgency: str = "routine",
    preferred_time: str | None = None,
    customer_message: str = "",
) -> dict[str, Any]:
    """Record a callback request and return the stored record."""
    name = clean_text(customer_name, field="customer_name", max_length=80)
    phone = normalise_phone(customer_phone or "")
    if not phone:
        raise ValidationError(
            "customer_phone is not a usable phone number (expected e.g. 082 123 4567)"
        )
    safe_message, _ = redact_sensitive(customer_message)

    return store.append(
        "callback_requests",
        {
            "conversation_id": conversation_id,
            "customer_name": name,
            "customer_phone": phone,
            "customer_phone_as_typed": (customer_phone or "").strip(),
            "reason": clean_text(reason, field="reason", max_length=120),
            "urgency": urgency,
            "preferred_time": (
                clean_text(preferred_time, field="preferred_time", max_length=80)
                if preferred_time
                else None
            ),
            "customer_message": safe_message,
            "status": "open",
            "source": "whatsapp_receptionist",
        },
        record_id=new_record_id("CB"),
    )
