"""Small shared objects used by the ORCHESTRATION layer.

Kept free of imports from other project modules so there is no circular import
between the brain, the router and the response builder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    """What we remember about one customer conversation.

    This is in-memory only for the prototype: restarting the program starts a
    fresh conversation.  The transcript is still saved to disk.
    """

    conversation_id: str
    customer_name: str | None = None
    customer_phone: str | None = None

    # "contact_details" while we are waiting for a name/number.
    pending: str | None = None
    pending_reason: str | None = None
    pending_urgency: str | None = None

    # Escalations already created, keyed by "<reason>:<intent>", so repeating
    # the same question does not spam staff with duplicate alerts.
    escalations: dict[str, str] = field(default_factory=dict)
    callback_id: str | None = None

    # How the first alert for this conversation was delivered (for wording).
    notified_ok: bool | None = None
    notified_simulated: bool | None = None

    turns: int = 0
    last_intent: str | None = None

    @property
    def has_contact_details(self) -> bool:
        return bool(self.customer_name and self.customer_phone)


@dataclass
class TurnActions:
    """What the system actually did while handling one message.

    The response builder reads this to decide what it is allowed to claim.
    """

    needs_staff: bool = False
    escalation_id: str | None = None
    escalation_reason: str | None = None
    escalation_priority: str | None = None
    callback_id: str | None = None

    notification_ok: bool | None = None
    notification_channel: str | None = None
    notification_simulated: bool | None = None
    notification_detail: str | None = None

    details_captured: bool = False
    privacy_warning: bool = False
    followed_up_on: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "needs_staff": self.needs_staff,
            "escalation_id": self.escalation_id,
            "escalation_reason": self.escalation_reason,
            "escalation_priority": self.escalation_priority,
            "callback_id": self.callback_id,
            "notification_ok": self.notification_ok,
            "notification_channel": self.notification_channel,
            "notification_simulated": self.notification_simulated,
            "notification_detail": self.notification_detail,
            "details_captured": self.details_captured,
            "privacy_warning": self.privacy_warning,
        }


@dataclass(frozen=True)
class TurnResult:
    """Everything one turn produced, for callers, logs and tests."""

    conversation_id: str
    reply: str
    intent_name: str
    intent_confidence: float
    urgency: str
    needs_human: bool
    actions: TurnActions
    delivery: dict[str, Any]
    session: Session
