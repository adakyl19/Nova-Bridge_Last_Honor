"""Turn an inbound WhatsApp payload (or a typed local message) into a clean object.

Two entry points:

1. `parse_whatsapp_webhook(payload)` - understands the exact JSON shape that
   Meta's WhatsApp Cloud API posts to your webhook.  It is NOT connected to
   WhatsApp yet; it is written and tested offline so that Phase 6 (going live)
   is a switch-on rather than a rewrite.

2. `from_local_text(...)` - what the console chat uses while we develop.

Both return the same `IncomingMessage`, so the rest of the system does not know
or care where a message came from.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # allow running as a script
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.storage import ValidationError, clean_text


@dataclass(frozen=True)
class IncomingMessage:
    conversation_id: str
    sender: str
    text: str
    received_at: str
    channel: str = "local"
    whatsapp_message_id: str | None = None
    contact_name: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def from_local_text(
    text: str,
    *,
    conversation_id: str = "local-demo",
    sender: str = "local-customer",
) -> IncomingMessage:
    """Build an IncomingMessage from something typed into the console."""
    return IncomingMessage(
        conversation_id=clean_text(conversation_id, field="conversation_id", max_length=120),
        sender=sender,
        text=text if isinstance(text, str) else "",
        received_at=_now(),
        channel="local",
    )


def parse_whatsapp_webhook(payload: dict[str, Any]) -> list[IncomingMessage]:
    """Extract text messages from a WhatsApp Cloud API webhook body.

    Only text messages are handled for now. Images, audio, documents and
    stickers produce no IncomingMessage: the caller should reply asking the
    customer to type their message (that behaviour arrives with Phase 6).
    """
    messages: list[IncomingMessage] = []
    if not isinstance(payload, dict):
        return messages

    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}
            contacts = value.get("contacts", []) or []
            name_by_wa_id = {
                str(contact.get("wa_id")): (contact.get("profile") or {}).get("name")
                for contact in contacts
                if isinstance(contact, dict) and contact.get("wa_id")
            }
            for message in value.get("messages", []) or []:
                if not isinstance(message, dict) or message.get("type") != "text":
                    continue
                sender = str(message.get("from", "")).strip()
                body = (message.get("text") or {}).get("body", "")
                if not sender or not isinstance(body, str) or not body.strip():
                    continue
                messages.append(
                    IncomingMessage(
                        conversation_id=sender,
                        sender=sender,
                        text=body,
                        received_at=_now(),
                        channel="whatsapp",
                        whatsapp_message_id=message.get("id"),
                        contact_name=name_by_wa_id.get(sender),
                    )
                )
    return messages


def validate(message: IncomingMessage) -> IncomingMessage:
    """Reject messages we cannot safely process."""
    if not message.text or not message.text.strip():
        raise ValidationError("message text is empty")
    if len(message.text) > 4000:
        raise ValidationError("message text is longer than WhatsApp allows")
    return message
