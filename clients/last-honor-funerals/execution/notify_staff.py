"""Alert a human member of staff about a matter that needs them.

Three separate things, which the receptionist must never confuse:
    1. an escalation/request was recorded   (a file was written)
    2. an alert was delivered to staff      (this module reports ok=True/False)
    3. a staff member responded             (only a person can make this true)

Right now alerts go to a local staff inbox file: that is a simulation, and
`simulated=True` says so.  If STAFF_ALERT_EMAIL is set we still cannot send
email (no email integration has been approved or configured), so the result is
ok=False and the customer-facing wording stays cautious.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings, load_settings
from execution.storage import Store, clean_text, new_record_id, normalise_phone, redact_sensitive


@dataclass(frozen=True)
class StaffNotificationResult:
    ok: bool
    channel: str
    simulated: bool
    detail: str
    record_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "channel": self.channel,
            "simulated": self.simulated,
            "detail": self.detail,
            "record_id": self.record_id,
        }


def notify_staff(
    store: Store,
    settings: Settings | None = None,
    *,
    subject: str,
    summary: str,
    urgency: str = "normal",
    conversation_id: str = "",
    customer_name: str | None = None,
    customer_phone: str | None = None,
    related_record_id: str | None = None,
) -> StaffNotificationResult:
    """Write an alert to the staff inbox and report whether it was delivered."""
    settings = settings or load_settings()
    safe_summary, redacted = redact_sensitive(
        clean_text(summary, field="summary", max_length=1000)
    )

    record = store.append(
        "staff_notifications",
        {
            "subject": clean_text(subject, field="subject", max_length=160),
            "summary": safe_summary,
            "urgency": urgency,
            "conversation_id": conversation_id,
            "customer_name": customer_name,
            "customer_phone": normalise_phone(customer_phone or "") or customer_phone,
            "related_record_id": related_record_id,
            "channel": "local-staff-inbox",
            "simulated": True,
            "redacted": redacted,
            "delivered_to_human": False,
        },
        record_id=new_record_id("NOTE"),
    )

    if settings.staff_alert_email:
        return StaffNotificationResult(
            ok=False,
            channel="email",
            simulated=False,
            detail=(
                "STAFF_ALERT_EMAIL is set but email delivery is not configured. "
                "The alert was only recorded in the local staff inbox."
            ),
            record_id=record["record_id"],
        )

    return StaffNotificationResult(
        ok=True,
        channel="local-staff-inbox",
        simulated=True,
        detail=(
            "Recorded in the local staff inbox "
            f"({store.path_for('staff_notifications').name}). No person was alerted."
        ),
        record_id=record["record_id"],
    )
