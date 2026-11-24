"""Record conversations, enquiries and escalations.

These functions are the "paper trail" of the receptionist.  They only write;
they never decide what the receptionist should say.

Privacy: message text is passed through `redact_sensitive()` before it is
written, so an ID number or banking detail a customer typed by mistake is not
stored in the logs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.storage import Store, clean_text, new_record_id, redact_sensitive, utc_now


def log_turn(
    store: Store,
    *,
    conversation_id: str,
    direction: str,
    text: str,
    channel: str = "local",
    intent: str | None = None,
) -> dict[str, Any]:
    """Append one line of the conversation transcript."""
    if direction not in {"inbound", "outbound"}:
        raise ValueError("direction must be 'inbound' or 'outbound'")
    safe_text, redacted = redact_sensitive(text)
    return store.append(
        "conversation_log",
        {
            "conversation_id": conversation_id,
            "direction": direction,
            "channel": channel,
            "intent": intent,
            "text": safe_text,
            "redacted": redacted,
        },
    )


def log_enquiry(
    store: Store,
    *,
    conversation_id: str,
    intent: str,
    urgency: str,
    customer_message: str,
    reply: str,
    customer_name: str | None = None,
    customer_phone: str | None = None,
    escalated: bool = False,
    escalation_reason: str | None = None,
    notification_ok: bool | None = None,
    channel: str = "local",
) -> dict[str, Any]:
    """Record what the customer asked and how the receptionist responded."""
    safe_message, redacted = redact_sensitive(customer_message)
    record = store.append(
        "enquiries",
        {
            "conversation_id": conversation_id,
            "channel": channel,
            "intent": intent,
            "urgency": urgency,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_message": safe_message,
            "redacted": redacted,
            "reply": reply,
            "escalated": escalated,
            "escalation_reason": escalation_reason,
            "staff_notification_ok": notification_ok,
            "recorded_at": utc_now(),
        },
    )
    return record


def log_escalation(
    store: Store,
    *,
    conversation_id: str,
    reason: str,
    priority: str,
    summary: str,
    customer_name: str | None,
    customer_phone: str | None,
    customer_message: str,
    notification: dict[str, Any] | None = None,
    callback_id: str | None = None,
    record_id: str | None = None,
) -> dict[str, Any]:
    """Record a matter that needs a human.

    `status` starts as "open" and is only ever changed by a person (there is no
    code path that marks an escalation as handled).
    """
    safe_message, redacted = redact_sensitive(customer_message)
    return store.append(
        "escalations",
        {
            "conversation_id": conversation_id,
            "reason": reason,
            "priority": priority,
            "summary": clean_text(summary, field="summary", max_length=500),
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_message": safe_message,
            "redacted": redacted,
            "callback_id": callback_id,
            "staff_notification": notification,
            "status": "open",
            "assigned_to": None,
            "resolved_at": None,
        },
        record_id=record_id or new_record_id("ESC"),
    )
