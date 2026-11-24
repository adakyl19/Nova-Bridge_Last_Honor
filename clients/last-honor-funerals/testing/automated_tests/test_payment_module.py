"""Checks for the payment reminder module: it must plan, and never send.

Run from clients/last-honor-funerals:
    python -m unittest discover -s testing/automated_tests -t . -v
"""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import load_settings
from execution.payment.check_payment_status import (
    PaymentDataNotAvailable,
    assert_verified_dataset,
    check_payment_status,
    load_records,
)
from execution.payment.send_payment_reminder import (
    ReminderSendBlocked,
    load_policy,
    plan_reminders,
    send_reminders,
)

RECORDS = PROJECT_ROOT / "data" / "payment_records.sample.json"
POLICY = PROJECT_ROOT / "data" / "payment_reminder_policy.json"


class PaymentLookupTests(unittest.TestCase):
    def test_sample_dataset_is_marked_fictional(self):
        dataset_kind, records = load_records(RECORDS)
        self.assertEqual(dataset_kind, "fictional")
        self.assertEqual(len(records), 5)

    def test_lookup_returns_a_record_but_flags_it_as_sample(self):
        lookup = check_payment_status(phone="082 000 0001", records_path=RECORDS)
        self.assertEqual(lookup.status, "sample_only")
        self.assertIsNotNone(lookup.record)
        self.assertEqual(lookup.record.account_ref, "LHF-TEST-0001")
        self.assertFalse(lookup.usable_with_customer)

    def test_lookup_by_account_reference(self):
        lookup = check_payment_status(account_ref="lhf-test-0005", records_path=RECORDS)
        self.assertEqual(lookup.status, "sample_only")
        self.assertEqual(lookup.record.customer_name, "Test Customer Echo")

    def test_unknown_customer_is_not_found(self):
        lookup = check_payment_status(phone="082 999 9999", records_path=RECORDS)
        self.assertEqual(lookup.status, "not_found")
        self.assertIsNone(lookup.record)

    def test_missing_query_is_invalid(self):
        self.assertEqual(check_payment_status(records_path=RECORDS).status, "invalid")

    def test_fictional_data_cannot_be_treated_as_real(self):
        with self.assertRaises(PaymentDataNotAvailable):
            assert_verified_dataset("fictional")


class ReminderPlanTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy(POLICY)
        self.dataset_kind, self.records = load_records(RECORDS)

    def plan(self, today: date):
        return plan_reminders(
            self.records, self.policy, today=today, dataset_kind=self.dataset_kind
        )

    def test_policy_is_unapproved_draft(self):
        self.assertEqual(self.policy["status"], "draft")
        self.assertFalse(self.policy["approved_by_owner"])
        self.assertFalse(self.policy["templates_approved"])

    def test_only_eligible_accounts_are_planned(self):
        plan = self.plan(date(2026, 11, 24))
        refs = {reminder.account_ref for reminder in plan.reminders}
        self.assertEqual(refs, {"LHF-TEST-0001", "LHF-TEST-0005"})

        skipped = {item["account_ref"]: item["reason"] for item in plan.skipped}
        self.assertEqual(skipped["LHF-TEST-0002"], "no outstanding balance")
        self.assertEqual(skipped["LHF-TEST-0003"], "customer asked reminders to stop")
        self.assertIn("dispute", skipped["LHF-TEST-0004"])

    def test_stage_and_amount_come_from_the_policy_and_record(self):
        plan = self.plan(date(2026, 11, 24))
        by_ref = {reminder.account_ref: reminder for reminder in plan.reminders}
        self.assertEqual(by_ref["LHF-TEST-0001"].stage, "second")
        self.assertEqual(by_ref["LHF-TEST-0005"].stage, "first")
        self.assertIn("ZAR 4,500.00", by_ref["LHF-TEST-0001"].message)
        self.assertIn("Test Customer Alpha", by_ref["LHF-TEST-0001"].message)

    def test_first_reminder_waits_for_the_interval(self):
        plan = self.plan(date(2026, 11, 21))  # 0005 is only 1 day overdue
        refs = {reminder.account_ref for reminder in plan.reminders}
        self.assertEqual(refs, {"LHF-TEST-0001"})

    def test_reminders_stop_at_the_maximum(self):
        policy = dict(self.policy)
        policy["max_reminders_per_account"] = 1
        plan = plan_reminders(
            self.records, policy, today=date(2026, 11, 24), dataset_kind=self.dataset_kind
        )
        for reminder in plan.reminders:
            self.assertEqual(reminder.stage, "first")
        self.assertNotIn("LHF-TEST-0001", {r.account_ref for r in plan.reminders})

    def test_sending_is_blocked_even_with_confirmation(self):
        plan = self.plan(date(2026, 11, 24))
        settings = replace(
            load_settings(dotenv_path=PROJECT_ROOT / "data" / "absent.env"),
            payment_reminders_enabled=True,
        )
        with self.assertRaises(ReminderSendBlocked) as caught:
            send_reminders(plan, self.policy, settings, confirm_send=True)
        message = str(caught.exception)
        self.assertIn("owner has not approved", message)
        self.assertIn("verified payment records", message)
        self.assertIn("WhatsApp transport", message)

    def test_sending_is_blocked_by_default(self):
        plan = self.plan(date(2026, 11, 24))
        with self.assertRaises(ReminderSendBlocked):
            send_reminders(plan, self.policy)


if __name__ == "__main__":
    unittest.main(verbosity=2)
