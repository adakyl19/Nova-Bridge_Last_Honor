"""Chat with the receptionist locally. No WhatsApp, no API keys, no cost.

Usage (from clients/last-honor-funerals):

    python run_local_chat.py
    python run_local_chat.py --message "My father passed away this morning"
    python run_local_chat.py --message "What are your prices?" --trace

Commands inside the chat:
    /quit     leave
    /reset    forget this conversation (start as a new customer)
    /trace    show or hide the intent/escalation details for each turn

Every reply is written by the local rule-based provider. Nothing is sent to
WhatsApp. Staff alerts are recorded in data/runtime/, not delivered to a person.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import load_settings
from execution.receive_message import from_local_text
from execution.send_message import MessagingNotConfigured
from orchestration.receptionist_brain import ReceptionistBrain

BANNER = """\
Last Honor Funerals - AI Receptionist (LOCAL SIMULATION)
--------------------------------------------------------
* Replies come from the free local provider. No AI API is called.
* No WhatsApp message is sent; replies are printed here.
* Staff alerts are written to data/runtime/, not delivered to a person.
* Business details are NOT approved yet - placeholders are never shown.
Commands: /quit  /reset  /trace
"""


def _print_trace(result) -> None:
    actions = result.actions
    print(
        f"   [trace] intent={result.intent_name} "
        f"confidence={result.intent_confidence:.2f} "
        f"urgency={result.urgency} "
        f"needs_human={result.needs_human}"
    )
    if actions.escalation_id:
        print(f"   [trace] escalation={actions.escalation_id} ({actions.escalation_reason})")
    if actions.callback_id:
        print(f"   [trace] callback_request={actions.callback_id}")
    if actions.notification_ok is not None:
        print(
            f"   [trace] staff_notification ok={actions.notification_ok} "
            f"channel={actions.notification_channel} "
            f"simulated={actions.notification_simulated}"
        )
        if actions.notification_detail:
            print(f"   [trace] {actions.notification_detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local receptionist chat (simulation).")
    parser.add_argument("--message", "-m", help="send one message and exit")
    parser.add_argument("--conversation-id", default="local-demo")
    parser.add_argument("--trace", action="store_true", help="show intent and escalation details")
    args = parser.parse_args(argv)

    try:
        settings = load_settings()
        brain = ReceptionistBrain(settings=settings)
    except MessagingNotConfigured as exc:
        print(f"Configuration problem: {exc}")
        return 2

    conversation_id = args.conversation_id
    print(BANNER)
    print(f"Conversation id: {conversation_id}")
    print(f"Data folder:     {settings.data_dir}")
    print(f"Provider:        {brain.provider.name}")
    if not brain.profile.approved:
        missing = len(brain.profile.missing())
        print(f"Business facts:  {missing} field(s) unverified - the receptionist will offer")
        print("                 a human instead of guessing.")
    print("")

    if args.message:
        result = brain.handle(
            from_local_text(args.message, conversation_id=conversation_id)
        )
        if args.trace:
            _print_trace(result)
        return 0

    show_trace = args.trace
    while True:
        try:
            text = input("Customer: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0

        if not text:
            continue
        if text.lower() in {"/quit", "/exit", "quit", "exit"}:
            print("Goodbye.")
            return 0
        if text.lower() == "/reset":
            brain.reset(conversation_id)
            print("[conversation reset]\n")
            continue
        if text.lower() == "/trace":
            show_trace = not show_trace
            print(f"[trace {'on' if show_trace else 'off'}]\n")
            continue

        result = brain.handle(from_local_text(text, conversation_id=conversation_id))
        if show_trace:
            _print_trace(result)
        print("")


if __name__ == "__main__":
    raise SystemExit(main())
