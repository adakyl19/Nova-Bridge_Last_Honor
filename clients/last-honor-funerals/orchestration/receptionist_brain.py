"""The ORCHESTRATION layer: one customer message in, one careful reply out.

For every message the brain:
    1. reads the customer's name / phone number if they offered them;
    2. classifies the intent (intent_router, or a future live provider);
    3. decides whether a human is needed;
    4. calls the execution layer (record, escalate, notify) if so;
    5. asks the response builder for wording that matches what really happened;
    6. logs the turn and hands the reply to the transport.

It never invents business facts and never sends a payment reminder.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings, load_settings
from execution.create_callback_request import create_callback_request
from execution.log_enquiry import log_enquiry, log_escalation, log_turn
from execution.notify_staff import notify_staff
from execution.read_business_profile import BusinessProfile, load_profile
from execution.receive_message import IncomingMessage, validate
from execution.send_message import DeliveryResult, Transport, get_transport
from execution.storage import Store, ValidationError, new_record_id
from orchestration.ai_provider import IntentProvider, get_intent_provider
from orchestration.detail_extractor import CustomerDetails, extract_details
from orchestration.models import Session, TurnActions, TurnResult
from orchestration.response_builder import build_reply

# Intents that always need a person, whatever the business profile says.
STAFF_INTENTS = {
    "death_notification",
    "collection_request",
    "funeral_arrangements",
    "callback_request",
    "human_handoff",
    "complaint",
    "unknown",
    "payment_balance_query",
    "payment_claim_paid",
    "payment_arrangement",
    "payment_dispute",
    "payment_stop_reminders",
}

# Intents answered from the approved business profile (escalate only if missing).
INFO_FACT_BY_INTENT = {
    "address": "address",
    "opening_hours": "opening_hours",
    "pricing": "prices",
    "services": "services",
    "contact_details": "phone",
}

PRIORITY_BY_URGENCY = {
    "urgent": "urgent",
    "sensitive": "high",
    "routine": "normal",
}

INTENT_SUMMARY = {
    "death_notification": "Customer reports a death and needs assistance",
    "collection_request": "URGENT: customer needs a collection",
    "funeral_arrangements": "Customer wants to discuss funeral arrangements",
    "callback_request": "Customer asked for a callback",
    "human_handoff": "Customer asked to speak to a person",
    "complaint": "Customer complaint",
    "unknown": "Question the receptionist could not answer from approved information",
    "payment_balance_query": "Customer asked about their account balance",
    "payment_claim_paid": "Customer says a payment was made",
    "payment_arrangement": "Customer asked about payment arrangements",
    "payment_dispute": "Customer disputes an amount",
    "payment_stop_reminders": "Customer asked for payment reminders to stop",
    "address": "Customer asked for the address (not verified yet)",
    "opening_hours": "Customer asked about opening hours (not verified yet)",
    "pricing": "Customer asked about prices (not approved yet)",
    "services": "Customer asked about services (not approved yet)",
    "contact_details": "Customer asked for contact details (not verified yet)",
}

EMPTY_MESSAGE_REPLY = (
    "I'm sorry, I didn't receive that. Could you please type your message again?"
)

TOO_LONG_REPLY = (
    "I'm sorry, that message is too long for me to read. Could you please send it "
    "in a shorter message?"
)


class ReceptionistBrain:
    """Stateful receptionist: remembers conversations in memory while running."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        store: Store | None = None,
        profile: BusinessProfile | None = None,
        transport: Transport | None = None,
        provider: IntentProvider | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.store = store or Store(self.settings.data_dir)
        self.profile = profile or load_profile(self.settings.business_profile_path)
        self.transport = transport or get_transport(self.settings, self.store)
        self.provider = provider or get_intent_provider(self.settings)
        self._sessions: dict[str, Session] = {}

    # -- session handling ---------------------------------------------------
    def session(self, conversation_id: str) -> Session:
        if conversation_id not in self._sessions:
            self._sessions[conversation_id] = Session(conversation_id=conversation_id)
        return self._sessions[conversation_id]

    def reset(self, conversation_id: str) -> None:
        self._sessions.pop(conversation_id, None)

    # -- decision helpers ---------------------------------------------------
    def _needs_staff(self, intent_name: str) -> bool:
        if intent_name in STAFF_INTENTS:
            return True
        fact_key = INFO_FACT_BY_INTENT.get(intent_name)
        if fact_key and not self.profile.is_available(fact_key):
            return True
        return False

    @staticmethod
    def _escalation_reason(intent_name: str) -> str:
        return (
            "unanswered_information_request"
            if intent_name in INFO_FACT_BY_INTENT
            else intent_name
        )

    @staticmethod
    def _merge_details(session: Session, details: CustomerDetails) -> bool:
        changed = False
        if details.name and not session.customer_name:
            session.customer_name = details.name
            changed = True
        if details.phone and not session.customer_phone:
            session.customer_phone = details.phone
            changed = True
        return changed

    def _record_followup(
        self,
        session: Session,
        message: IncomingMessage,
        intent_name: str,
        actions: TurnActions,
        *,
        existing_escalation: str | None = None,
    ) -> None:
        """Create a callback request and (if needed) the staff alert."""
        if (
            session.has_contact_details
            and session.callback_id is None
            and intent_name in STAFF_INTENTS
        ):
            callback = create_callback_request(
                self.store,
                conversation_id=session.conversation_id,
                customer_name=session.customer_name,
                customer_phone=session.customer_phone,
                reason=intent_name,
                urgency=PRIORITY_BY_URGENCY.get(session.pending_urgency or "sensitive", "normal"),
                customer_message=message.text,
            )
            session.callback_id = callback["record_id"]
            actions.callback_id = callback["record_id"]

        notification = notify_staff(
            self.store,
            self.settings,
            subject=INTENT_SUMMARY.get(intent_name, "Customer message"),
            summary=(
                f"{INTENT_SUMMARY.get(intent_name, 'Customer message')}. "
                f"Customer message: {message.text}"
            ),
            urgency="high",
            conversation_id=session.conversation_id,
            customer_name=session.customer_name,
            customer_phone=session.customer_phone,
            related_record_id=actions.callback_id or existing_escalation,
        )
        actions.notification_ok = notification.ok
        actions.notification_channel = notification.channel
        actions.notification_simulated = notification.simulated
        actions.notification_detail = notification.detail

    # -- main entry point ---------------------------------------------------
    def handle(self, message: IncomingMessage) -> TurnResult:
        session = self.session(message.conversation_id)
        session.turns += 1

        if not message.text or not message.text.strip():
            return self._finish(
                session,
                message,
                reply=EMPTY_MESSAGE_REPLY,
                intent_name="invalid",
                confidence=0.0,
                urgency="routine",
                actions=TurnActions(),
            )

        try:
            validate(message)
        except ValidationError:
            return self._finish(
                session,
                message,
                reply=TOO_LONG_REPLY,
                intent_name="invalid",
                confidence=0.0,
                urgency="routine",
                actions=TurnActions(),
            )

        details = extract_details(
            message.text, expect_name=session.pending == "contact_details"
        )
        new_details = self._merge_details(session, details)
        intent = self.provider.classify(message.text)

        continuation = session.pending == "contact_details" and new_details
        intent_name = (session.pending_reason or intent.intent) if continuation else intent.intent
        needs_staff = self._needs_staff(intent_name)

        actions = TurnActions(
            needs_staff=needs_staff,
            privacy_warning=details.had_sensitive_details,
            followed_up_on=intent_name,
        )

        # A reply that supplies details keeps the urgency of the matter it belongs to.
        urgency = (session.pending_urgency or intent.urgency) if continuation else intent.urgency

        if continuation:
            actions.escalation_reason = self._escalation_reason(intent_name)
            actions.escalation_priority = PRIORITY_BY_URGENCY.get(urgency, "normal")
            actions.details_captured = session.has_contact_details
            if actions.details_captured:
                # The callback + alert for this reason were already recorded on
                # the turn that asked for details; reuse that escalation id.
                key = f"{self._escalation_reason(intent_name)}:{intent_name}"
                self._record_followup(
                    session, message, intent_name, actions, existing_escalation=session.escalations.get(key)
                )
                session.pending = None
                session.pending_reason = None
                session.pending_urgency = None
        elif needs_staff:
            actions.escalation_reason = self._escalation_reason(intent_name)
            actions.escalation_priority = PRIORITY_BY_URGENCY.get(urgency, "normal")
            key = f"{actions.escalation_reason}:{intent_name}"
            if key in session.escalations:
                # Same matter again: do not create a duplicate alert.
                actions.escalation_id = session.escalations[key]
                actions.notification_ok = session.notified_ok
                actions.notification_simulated = session.notified_simulated
            else:
                if session.has_contact_details and session.callback_id is None:
                    callback = create_callback_request(
                        self.store,
                        conversation_id=session.conversation_id,
                        customer_name=session.customer_name,
                        customer_phone=session.customer_phone,
                        reason=intent_name,
                        urgency=actions.escalation_priority or "normal",
                        customer_message=message.text,
                    )
                    session.callback_id = callback["record_id"]
                    actions.callback_id = callback["record_id"]

                escalation_id = new_record_id("ESC")
                notification = notify_staff(
                    self.store,
                    self.settings,
                    subject=INTENT_SUMMARY.get(intent_name, "Customer message"),
                    summary=(
                        f"{INTENT_SUMMARY.get(intent_name, 'Customer message')}. "
                        f"Customer message: {message.text}"
                    ),
                    urgency=actions.escalation_priority,
                    conversation_id=session.conversation_id,
                    customer_name=session.customer_name,
                    customer_phone=session.customer_phone,
                    related_record_id=actions.callback_id or escalation_id,
                )
                log_escalation(
                    self.store,
                    record_id=escalation_id,
                    conversation_id=session.conversation_id,
                    reason=actions.escalation_reason,
                    priority=actions.escalation_priority,
                    summary=INTENT_SUMMARY.get(intent_name, "Customer message"),
                    customer_name=session.customer_name,
                    customer_phone=session.customer_phone,
                    customer_message=message.text,
                    notification=notification.as_dict(),
                    callback_id=actions.callback_id,
                )
                session.escalations[key] = escalation_id
                session.notified_ok = notification.ok
                session.notified_simulated = notification.simulated
                actions.escalation_id = escalation_id
                actions.notification_ok = notification.ok
                actions.notification_channel = notification.channel
                actions.notification_simulated = notification.simulated
                actions.notification_detail = notification.detail

            if needs_staff and not session.has_contact_details:
                session.pending = "contact_details"
                session.pending_reason = intent_name
                session.pending_urgency = urgency
            else:
                session.pending = None
                session.pending_reason = None
                session.pending_urgency = None

        if not needs_staff:
            session.pending = None
            session.pending_reason = None
            session.pending_urgency = None

        reply = build_reply(
            intent_name=intent_name,
            profile=self.profile,
            actions=actions,
            session=session,
            continuation=continuation,
        )
        session.last_intent = intent_name

        return self._finish(
            session,
            message,
            reply=reply,
            intent_name=intent_name,
            confidence=intent.confidence,
            urgency=urgency,
            actions=actions,
        )

    # -- logging + delivery -------------------------------------------------
    def _finish(
        self,
        session: Session,
        message: IncomingMessage,
        *,
        reply: str,
        intent_name: str,
        confidence: float,
        urgency: str,
        actions: TurnActions,
    ) -> TurnResult:
        delivery: DeliveryResult = self.transport.send(to=message.sender, text=reply)

        log_turn(
            self.store,
            conversation_id=session.conversation_id,
            direction="inbound",
            text=message.text,
            channel=message.channel,
            intent=intent_name,
        )
        log_turn(
            self.store,
            conversation_id=session.conversation_id,
            direction="outbound",
            text=reply,
            channel=delivery.channel,
            intent=intent_name,
        )
        log_enquiry(
            self.store,
            conversation_id=session.conversation_id,
            intent=intent_name,
            urgency=urgency,
            customer_message=message.text,
            reply=reply,
            customer_name=session.customer_name,
            customer_phone=session.customer_phone,
            escalated=actions.needs_staff,
            escalation_reason=actions.escalation_reason,
            notification_ok=actions.notification_ok,
            channel=delivery.channel,
        )

        return TurnResult(
            conversation_id=session.conversation_id,
            reply=reply,
            intent_name=intent_name,
            intent_confidence=confidence,
            urgency=urgency,
            needs_human=actions.needs_staff,
            actions=actions,
            delivery=delivery.as_dict(),
            session=session,
        )
