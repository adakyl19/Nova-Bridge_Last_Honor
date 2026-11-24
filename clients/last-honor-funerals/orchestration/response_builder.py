"""Write the words the customer sees.

Every sentence here has one job: be kind, be clear, and never state something
the system cannot back up.  In particular:

- business facts come from the approved profile or are not stated at all;
- "our team has been alerted" is only used when a real (non-simulated)
  notification was delivered;
- no price, balance or due date is ever produced by this module.

The wording follows directives/receptionist.md and directives/human-escalation.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.read_business_profile import BusinessProfile
from execution.storage import format_phone_for_display
from orchestration.models import Session, TurnActions

PRIVACY_NOTE = (
    "Please don't send ID numbers or banking details on WhatsApp - "
    "I've left that out of what I recorded."
)

# Which team a message is being recorded for (used in the wording).
TEAM_BY_INTENT = {
    "death_notification": "our funeral arrangements team",
    "funeral_arrangements": "our funeral arrangements team",
    "collection_request": "our collections team",
    "complaint": "our team",
    "human_handoff": "our team",
    "callback_request": "our team",
    "unknown": "our team",
    "payment_balance_query": "our accounts team",
    "payment_claim_paid": "our accounts team",
    "payment_arrangement": "our accounts team",
    "payment_dispute": "our accounts team",
    "payment_stop_reminders": "our accounts team",
}

# What was recorded, in plain language.
SUBJECT_BY_INTENT = {
    "death_notification": "message and request for assistance",
    "collection_request": "urgent collection request",
    "funeral_arrangements": "request to discuss funeral arrangements",
    "callback_request": "callback request",
    "human_handoff": "request to speak to a team member",
    "complaint": "complaint",
    "unknown": "question",
    "general_help": "message",
    "address": "request for our address",
    "opening_hours": "request for our opening hours",
    "pricing": "request for pricing",
    "services": "request for information about our services",
    "contact_details": "request for our contact details",
    "payment_balance_query": "account query",
    "payment_claim_paid": "message about a payment",
    "payment_arrangement": "payment arrangement request",
    "payment_dispute": "payment dispute",
    "payment_stop_reminders": "request to stop payment reminders",
}


def _joined(value: object) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def _base_reply(intent_name: str, profile: BusinessProfile) -> str:
    """The main sentence for this intent. Business facts only if verified."""
    if intent_name == "greeting":
        return (
            f"Good day, and thank you for contacting {profile.name}. "
            "How may I assist you today?"
        )

    if intent_name == "address":
        if profile.is_available("address"):
            return f"Our office is at {_joined(profile.value('address'))}."
        return (
            "I don't have a confirmed address to share yet, and I don't want to give "
            "you directions that might send you to the wrong place."
        )

    if intent_name == "opening_hours":
        if profile.is_available("opening_hours"):
            return f"Our opening hours are {_joined(profile.value('opening_hours'))}."
        return (
            "I can't confirm our opening hours yet, and I'd rather not give you times "
            "that might be wrong."
        )

    if intent_name == "pricing":
        if profile.is_available("prices"):
            return f"The approved pricing we have on file is: {_joined(profile.value('prices'))}."
        return (
            "I'm not able to give you a price I can't confirm. Funeral costs depend on "
            "the options a family chooses, so our team will send you the approved price list."
        )

    if intent_name == "services":
        if profile.is_available("services"):
            return f"We offer: {_joined(profile.value('services'))}."
        return (
            "I don't want to describe packages that haven't been confirmed for us yet. "
            "Our team can share the approved options with you."
        )

    if intent_name == "contact_details":
        if profile.is_available("phone"):
            return f"You can reach us on {_joined(profile.value('phone'))}."
        return "I don't have a confirmed number to give you yet."

    if intent_name == "death_notification":
        return (
            "I'm very sorry for your loss. We're here to help you through the next steps."
        )

    if intent_name == "collection_request":
        return (
            "I'm very sorry you're going through this. A collection request is urgent, "
            "so our team needs to attend to it quickly."
        )

    if intent_name == "funeral_arrangements":
        return (
            "I can help you get started with the funeral arrangements. Our funeral "
            "arrangements team will guide you through the options and the next steps."
        )

    if intent_name == "callback_request":
        return "Of course, I can arrange for our team to call you."

    if intent_name == "human_handoff":
        return "Of course. I'll ask a member of our team to contact you directly."

    if intent_name == "complaint":
        return (
            "I'm sorry for the frustration this has caused, and thank you for telling us. "
            "Our team needs to look into this properly."
        )

    if intent_name == "unknown":
        return (
            "I'm not sure I have a confirmed answer to that, and I don't want to give you "
            "information that might be incorrect. Our team can help you with it."
        )

    if intent_name == "general_help":
        return (
            "I'm here to help. Could you tell me a little more about what you need "
            "assistance with?"
        )

    if intent_name == "payment_balance_query":
        return (
            "I'm not able to view or discuss account balances on WhatsApp, and I don't "
            "want to give you information that might be wrong. Our accounts team can "
            "help you with your account."
        )

    if intent_name == "payment_claim_paid":
        return (
            "Thank you for letting me know. I can't confirm payments myself, so our "
            "accounts team needs to verify it."
        )

    if intent_name == "payment_arrangement":
        return (
            "I understand, and thank you for being open with us. Payment arrangements "
            "are handled by our accounts team."
        )

    if intent_name == "payment_dispute":
        return (
            "I'm sorry about that. Our accounts team needs to review the account "
            "before anything can be confirmed."
        )

    if intent_name == "payment_stop_reminders":
        return (
            "I understand. Payment reminders are handled by our accounts team, and "
            "they will need to review the account before anything changes."
        )

    if intent_name == "thanks":
        return "You're welcome. Please don't hesitate to message us if there's anything else we can help with."

    if intent_name == "goodbye":
        return f"Thank you for contacting {profile.name}. Take care."

    if intent_name == "invalid":
        return "I'm sorry, I didn't receive that. Could you please type your message again?"

    return "Thank you for your message."


def _alert_sentence(actions: TurnActions, intent_name: str) -> str:
    """Say only what actually happened to the staff alert."""
    if not actions.needs_staff:
        return ""
    subject = SUBJECT_BY_INTENT.get(intent_name, "message")
    if actions.notification_ok is None:
        return ""
    if actions.notification_ok and actions.notification_simulated:
        return f"I've recorded your {subject} in our system for our team to pick up."
    if actions.notification_ok:
        return f"I've alerted our team about your {subject}."
    return (
        f"I've recorded your {subject}, but I couldn't confirm that our team was "
        "alerted. If this is urgent, please phone us as soon as you can."
    )


def _ask_for_details(intent_name: str, session: Session) -> str:
    """Ask for the missing contact detail(s), or nothing if we have both."""
    if session.has_contact_details:
        return ""
    team = TEAM_BY_INTENT.get(intent_name, "our team")
    missing_name = not session.customer_name
    missing_phone = not session.customer_phone

    if missing_name and missing_phone:
        if intent_name == "callback_request":
            return (
                "May I have your name, the best number to call you on, and a good time "
                "for the call?"
            )
        if intent_name == "collection_request":
            return (
                f"May I please have your name, the best contact number for {team} to "
                "reach you on, and the town or suburb where your loved one is?"
            )
        return (
            f"May I please have your name and the best contact number for {team} "
            "to reach you on?"
        )
    if missing_name:
        return "May I also have your name so our team knows who to ask for?"
    return "May I also have the best contact number for our team to reach you on?"


def _confirmation(session: Session, actions: TurnActions, intent_name: str) -> str:
    """Thank the customer once their contact details are all we need."""
    team = TEAM_BY_INTENT.get(intent_name, "our team")
    name = session.customer_name or "there"
    phone = format_phone_for_display(session.customer_phone)
    text = (
        f"Thank you, {name}. I've recorded your details and your message for {team}, "
        f"and they can reach you on {phone}."
    )
    if actions.notification_ok and not actions.notification_simulated:
        text += " I've also alerted our team."
    elif actions.notification_ok:
        text += " It's in our system for our team to pick up."
    elif actions.notification_ok is False:
        text += (
            " I couldn't confirm that the alert reached our team, so please phone us "
            "if your matter is urgent."
        )
    return text


def build_reply(
    *,
    intent_name: str,
    profile: BusinessProfile,
    actions: TurnActions,
    session: Session,
    continuation: bool = False,
) -> str:
    """Compose one reply out of the pieces above."""
    sentences: list[str] = []

    if actions.privacy_warning:
        sentences.append(PRIVACY_NOTE)

    if actions.details_captured:
        sentences.append(
            _confirmation(session, actions, actions.followed_up_on or intent_name)
        )
    elif continuation:
        if session.customer_name:
            sentences.append(f"Thank you, {session.customer_name}.")
        else:
            sentences.append("Thank you.")
        ask = _ask_for_details(intent_name, session)
        if ask:
            sentences.append(ask)
    else:
        sentences.append(_base_reply(intent_name, profile))
        alert = _alert_sentence(actions, intent_name)
        if alert:
            sentences.append(alert)
        if actions.needs_staff:
            ask = _ask_for_details(intent_name, session)
            if ask:
                sentences.append(ask)

    return " ".join(sentence for sentence in sentences if sentence).strip()
