"""Automated checks for the receptionist (standard library only, no API calls).

Run from clients/last-honor-funerals:
    python -m unittest discover -s testing/automated_tests -t . -v

Each test covers one of the fifteen required conversations in
testing/test_cases.md, plus the safety rules that must never regress.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import load_settings
from execution.read_business_profile import load_profile
from execution.receive_message import from_local_text, parse_whatsapp_webhook
from execution.send_message import FileTransport
from execution.storage import Store
from orchestration.receptionist_brain import ReceptionistBrain

CONVERSATION = "conv-test"


class BrainHarness(unittest.TestCase):
    """Each test gets a fresh brain and a throw-away data folder."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.settings = replace(
            load_settings(dotenv_path=base / "absent.env"),
            data_dir=base / "runtime",
            business_profile_path=PROJECT_ROOT / "data" / "business_profile.json",
            message_transport="file",
            ai_provider="mock",
            enable_live_ai=False,
            payment_reminders_enabled=False,
            staff_alert_email="",
        )
        self.store = Store(self.settings.data_dir)
        self.brain = ReceptionistBrain(
            settings=self.settings,
            store=self.store,
            transport=FileTransport(self.store),
        )

    def say(self, text: str, conversation_id: str = CONVERSATION):
        return self.brain.handle(from_local_text(text, conversation_id=conversation_id))

    def escalations(self):
        return self.store.read("escalations")

    def callbacks(self):
        return self.store.read("callback_requests")

    def assert_no_placeholder_leak(self, reply: str) -> None:
        self.assertNotIn("[BUSINESS_", reply)
        self.assertNotIn("[APPROVED_", reply)
        self.assertNotIn("[STAFF_", reply)
        self.assertNotIn("[COLLECTION_", reply)
        self.assertNotIn("[OPENING_", reply)


class RequiredConversations(BrainHarness):
    # 1 -------------------------------------------------------------------
    def test_01_general_greeting(self):
        result = self.say("Good morning")
        self.assertEqual(result.intent_name, "greeting")
        self.assertFalse(result.actions.needs_staff)
        self.assertIn("Last Honor Funerals", result.reply)
        self.assertEqual(self.escalations(), [])

    # 2 -------------------------------------------------------------------
    def test_02_asks_for_address_without_inventing_one(self):
        result = self.say("Where are you located?")
        self.assertEqual(result.intent_name, "address")
        self.assertTrue(result.actions.needs_staff)
        self.assertIn("don't have a confirmed address", result.reply)
        self.assert_no_placeholder_leak(result.reply)
        self.assertEqual(len(self.escalations()), 1)
        self.assertEqual(
            self.escalations()[0]["reason"], "unanswered_information_request"
        )

    # 3 -------------------------------------------------------------------
    def test_03_asks_about_packages_without_inventing_them(self):
        result = self.say("What funeral packages do you offer?")
        self.assertEqual(result.intent_name, "services")
        self.assertIn("haven't been confirmed", result.reply)
        self.assert_no_placeholder_leak(result.reply)
        self.assertEqual(len(self.escalations()), 1)

    # 4 -------------------------------------------------------------------
    def test_04_asks_about_prices_without_quoting(self):
        result = self.say("How much does a funeral cost?")
        self.assertEqual(result.intent_name, "pricing")
        self.assertIn("price I can't confirm", result.reply)
        self.assertNotIn("R ", result.reply)
        self.assertNotIn("R0", result.reply)
        self.assert_no_placeholder_leak(result.reply)
        self.assertEqual(len(self.escalations()), 1)

    # 5 -------------------------------------------------------------------
    def test_05_reports_a_death(self):
        result = self.say("My father passed away this morning. We need assistance.")
        self.assertEqual(result.intent_name, "death_notification")
        self.assertTrue(result.needs_human)
        self.assertIn("very sorry for your loss", result.reply)
        self.assertIn("funeral arrangements team", result.reply)
        self.assertEqual(self.escalations()[0]["priority"], "high")
        # Simulated alert must not be described as a delivered notification.
        self.assertNotIn("notified", result.reply.lower())
        self.assertNotIn("has been alerted", result.reply.lower())

    def test_05b_death_details_become_a_callback_request(self):
        self.say("My mother passed away")
        result = self.say("My name is Thandi Mokoena and my number is 082 123 4567")
        self.assertIn("Thank you, Thandi Mokoena", result.reply)
        self.assertIn("082 123 4567", result.reply)
        callbacks = self.callbacks()
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(callbacks[0]["customer_phone"], "+27821234567")
        self.assertEqual(callbacks[0]["reason"], "death_notification")

    # 6 -------------------------------------------------------------------
    def test_06_collection_request_is_urgent(self):
        result = self.say("Please come and collect my father from the hospital.")
        self.assertEqual(result.intent_name, "collection_request")
        self.assertEqual(result.urgency, "urgent")
        self.assertEqual(self.escalations()[0]["priority"], "urgent")
        self.assertIn("urgent", result.reply.lower())

    # 7 -------------------------------------------------------------------
    def test_07_funeral_arrangements_go_to_staff(self):
        result = self.say("I need help with funeral arrangements for my sister")
        self.assertEqual(result.intent_name, "funeral_arrangements")
        self.assertTrue(result.actions.needs_staff)
        self.assertEqual(self.escalations()[0]["reason"], "funeral_arrangements")

    # 8 -------------------------------------------------------------------
    def test_08_callback_request(self):
        first = self.say("Please call me back")
        self.assertEqual(first.intent_name, "callback_request")
        self.assertIn("best number", first.reply)
        second = self.say("Thandi Mokoena, 082 555 1234")
        self.assertIn("Thandi Mokoena", second.reply)
        self.assertEqual(len(self.callbacks()), 1)
        self.assertEqual(len(self.escalations()), 1)  # not duplicated

    # 9 -------------------------------------------------------------------
    def test_09_asks_to_speak_to_a_human(self):
        result = self.say("I want to speak to a human please")
        self.assertEqual(result.intent_name, "human_handoff")
        self.assertTrue(result.actions.needs_staff)
        self.assertIn("member of our team", result.reply)

    # 10 ------------------------------------------------------------------
    def test_10_unknown_question_is_honest_and_escalated(self):
        result = self.say("Do you do Jewish funerals in Pretoria?")
        self.assertEqual(result.intent_name, "unknown")
        self.assertIn("not sure I have a confirmed answer", result.reply)
        self.assertEqual(len(self.escalations()), 1)

    # 11 ------------------------------------------------------------------
    def test_11_angry_customer_is_not_argued_with(self):
        result = self.say("This is unacceptable. No one has called me back!")
        self.assertEqual(result.intent_name, "complaint")
        self.assertIn("sorry for the frustration", result.reply)
        self.assertNotIn("calm down", result.reply.lower())
        self.assertEqual(len(self.escalations()), 1)

    # 12 ------------------------------------------------------------------
    def test_12_claiming_a_payment_is_never_confirmed(self):
        result = self.say("I already paid this account last week")
        self.assertEqual(result.intent_name, "payment_claim_paid")
        self.assertIn("can't confirm payments myself", result.reply)
        self.assertNotIn("payment has been received", result.reply.lower())
        self.assertEqual(len(self.escalations()), 1)

    # 13 ------------------------------------------------------------------
    def test_13_payment_arrangement_request(self):
        result = self.say("I can't afford the full amount, can we make a payment arrangement?")
        self.assertEqual(result.intent_name, "payment_arrangement")
        self.assertTrue(result.actions.needs_staff)
        self.assertEqual(self.escalations()[0]["reason"], "payment_arrangement")
        self.assertNotIn("R ", result.reply)

    # 14 ------------------------------------------------------------------
    def test_14_disputing_a_balance(self):
        result = self.say("I dispute this balance, the amount is wrong")
        self.assertEqual(result.intent_name, "payment_dispute")
        self.assertIn("accounts team", result.reply)

    # 15 ------------------------------------------------------------------
    def test_15_request_to_stop_reminders(self):
        result = self.say("Please stop sending me reminders")
        self.assertEqual(result.intent_name, "payment_stop_reminders")
        self.assertTrue(result.actions.needs_staff)
        self.assertNotIn("reminders have stopped", result.reply.lower())

    # extra: balance question never reveals a number -----------------------
    def test_balance_question_never_states_an_amount(self):
        result = self.say("How much do I owe on my account?")
        self.assertEqual(result.intent_name, "payment_balance_query")
        self.assertNotIn("R ", result.reply)
        self.assertNotIn("0.00", result.reply)
        self.assertIn("not able to view or discuss account balances", result.reply)


class SafetyRules(BrainHarness):
    def test_no_business_fact_is_invented_across_all_info_intents(self):
        for message in (
            "What are your opening hours on Saturday?",
            "What is your phone number?",
            "Do you have a price list?",
            "Which services do you offer?",
        ):
            with self.subTest(message=message):
                result = self.say(message)
                self.assert_no_placeholder_leak(result.reply)
                self.assertNotIn("Street", result.reply)
                self.assertNotIn("R", result.reply)

    def test_repeated_question_does_not_duplicate_the_escalation(self):
        self.say("What is your address?")
        self.say("I asked for your address?")
        self.assertEqual(len(self.escalations()), 1)

    def test_simulated_notification_is_reported_truthfully(self):
        result = self.say("My brother passed away")
        self.assertTrue(result.actions.notification_ok)
        self.assertTrue(result.actions.notification_simulated)
        self.assertIn("recorded", result.reply.lower())

    def test_privacy_note_and_redaction(self):
        result = self.say("My ID number is 8501015800081, my name is Test Person")
        self.assertIn("Please don't send ID numbers", result.reply)
        enquiry = self.store.read("enquiries")[-1]
        self.assertIn("[redacted", enquiry["customer_message"])
        self.assertTrue(enquiry["redacted"])

    def test_empty_message_is_handled(self):
        result = self.say("")
        self.assertEqual(result.intent_name, "invalid")
        self.assertIn("type your message again", result.reply)
        self.assertEqual(self.escalations(), [])

    def test_overlong_message_is_handled(self):
        result = self.say("a" * 5000)
        self.assertEqual(result.intent_name, "invalid")
        self.assertIn("too long", result.reply)

    def test_every_turn_is_logged(self):
        self.say("Hello")
        self.say("What are your prices?")
        self.assertEqual(len(self.store.read("enquiries")), 2)
        self.assertGreaterEqual(len(self.store.read("conversation_log")), 4)

    def test_phone_validation_rejects_nonsense(self):
        from execution.create_callback_request import create_callback_request
        from execution.storage import ValidationError

        with self.assertRaises(ValidationError):
            create_callback_request(
                self.store,
                conversation_id=CONVERSATION,
                customer_name="Test Person",
                customer_phone="not a number",
                reason="death_notification",
            )

    def test_conversation_reset_starts_fresh(self):
        self.say("My name is Thandi Mokoena, 082 123 4567")
        self.brain.reset(CONVERSATION)
        result = self.say("Where are you located?")
        self.assertIn("don't have a confirmed address", result.reply)


class BusinessProfileRules(unittest.TestCase):
    def test_profile_starts_unverified(self):
        profile = load_profile(PROJECT_ROOT / "data" / "business_profile.json")
        self.assertFalse(profile.approved)
        self.assertFalse(profile.is_available("address"))
        self.assertIsNone(profile.value("address"))
        self.assertEqual(len(profile.missing()), len(profile.facts))

    def test_verified_with_placeholder_is_still_unavailable(self):
        from execution.read_business_profile import BusinessProfile, Fact

        profile = BusinessProfile(
            name="Last Honor Funerals",
            country="South Africa",
            approved=False,
            facts={
                "address": Fact(
                    key="address",
                    status="verified",
                    value="[BUSINESS_ADDRESS]",
                    placeholder="[BUSINESS_ADDRESS]",
                )
            },
            source_path=Path("unused.json"),
        )
        self.assertFalse(profile.is_available("address"))

    def test_verified_real_value_is_available(self):
        from execution.read_business_profile import BusinessProfile, Fact

        profile = BusinessProfile(
            name="Last Honor Funerals",
            country="South Africa",
            approved=True,
            facts={
                "address": Fact(
                    key="address",
                    status="verified",
                    value="12 Example Street, TestTown",
                    placeholder="[BUSINESS_ADDRESS]",
                )
            },
            source_path=Path("unused.json"),
        )
        self.assertTrue(profile.is_available("address"))
        self.assertEqual(profile.value("address"), "12 Example Street, TestTown")


class WhatsAppPayloadParsing(unittest.TestCase):
    def test_parses_a_cloud_api_webhook_body(self):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "TEST_ACCOUNT",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "contacts": [
                                    {"wa_id": "27820000001", "profile": {"name": "Test Sender"}}
                                ],
                                "messages": [
                                    {
                                        "from": "27820000001",
                                        "id": "wamid.TEST",
                                        "timestamp": "1764000000",
                                        "type": "text",
                                        "text": {"body": "Hello, I need help"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        messages = parse_whatsapp_webhook(payload)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].text, "Hello, I need help")
        self.assertEqual(messages[0].conversation_id, "27820000001")
        self.assertEqual(messages[0].contact_name, "Test Sender")
        self.assertEqual(messages[0].channel, "whatsapp")

    def test_ignores_non_text_messages(self):
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {"from": "27820000001", "type": "image", "image": {}}
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        self.assertEqual(parse_whatsapp_webhook(payload), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
