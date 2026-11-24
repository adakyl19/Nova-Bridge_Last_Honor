"""Send an outbound reply, and report honestly whether it was delivered.

A `DeliveryResult` always says three things:
    ok        did the send actually succeed?
    channel   "console", "file" or "whatsapp"
    simulated True when nothing left this computer

The receptionist is only allowed to claim a message was delivered when
`ok` is True and `simulated` is False.  The WhatsApp transport is deliberately
not implemented yet: choosing it raises a clear error instead of silently
pretending to work (Phase 6 of the roadmap covers it).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from execution.storage import Store, clean_text


class MessagingNotConfigured(RuntimeError):
    """Raised when a live messaging channel is requested before it exists."""


@dataclass(frozen=True)
class DeliveryResult:
    ok: bool
    channel: str
    simulated: bool
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "channel": self.channel,
            "simulated": self.simulated,
            "detail": self.detail,
        }


class Transport(Protocol):
    channel: str
    simulated: bool

    def send(self, *, to: str, text: str) -> DeliveryResult: ...


class ConsoleTransport:
    """Prints the reply in the terminal. Nothing is sent anywhere."""

    channel = "console"
    simulated = True

    def send(self, *, to: str, text: str) -> DeliveryResult:
        body = clean_text(text, field="reply", max_length=4000)
        print(f"\nLast Honor Funerals (to {to}):\n{body}\n")
        return DeliveryResult(
            ok=True,
            channel=self.channel,
            simulated=True,
            detail="printed to the console; no WhatsApp message was sent",
        )


class FileTransport:
    """Writes the reply to data/runtime/outbox.jsonl (useful for tests)."""

    channel = "file"
    simulated = True

    def __init__(self, store: Store) -> None:
        self.store = store

    def send(self, *, to: str, text: str) -> DeliveryResult:
        body = clean_text(text, field="reply", max_length=4000)
        record = self.store.append("outbox", {"to": to, "text": body})
        return DeliveryResult(
            ok=True,
            channel=self.channel,
            simulated=True,
            detail=f"written to {self.store.path_for('outbox').name} ({record['record_id']})",
        )


class WhatsAppTransport:
    """Placeholder for Phase 6. Intentionally refuses to run."""

    channel = "whatsapp"
    simulated = False

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, *, to: str, text: str) -> DeliveryResult:
        raise MessagingNotConfigured(
            "WhatsApp delivery is not built yet. Phase 6 of the roadmap covers "
            "Meta Business, the Cloud API, a test number and webhooks. "
            "Nothing was sent."
        )


def get_transport(settings: Settings, store: Store | None = None) -> Transport:
    choice = settings.message_transport.strip().lower()
    if choice == "console":
        return ConsoleTransport()
    if choice == "file":
        return FileTransport(store or Store(settings.data_dir))
    if choice == "whatsapp":
        raise MessagingNotConfigured(
            "MESSAGE_TRANSPORT=whatsapp, but the WhatsApp integration has not been "
            "built or authorised yet. Use MESSAGE_TRANSPORT=console for now."
        )
    raise MessagingNotConfigured(
        f"Unknown MESSAGE_TRANSPORT {settings.message_transport!r}. "
        "Use 'console' or 'file'."
    )
