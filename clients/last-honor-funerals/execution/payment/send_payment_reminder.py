"""Build a payment-reminder plan - and refuse to send anything yet.

This is a design + simulation module.  It can:
    * load the draft reminder policy (intervals, caps, templates);
    * work out which fictional accounts would be due a reminder today;
    * show exactly what would be sent, and why each other account is skipped;
    * refuse to send, with a list of everything still needing approval.

It cannot send a reminder.  `send_reminders()` raises `ReminderSendBlocked`
unless (a) the owner has approved the policy and templates, (b) reminders are
switched on in configuration, (c) the data is real verified payment data, and
(d) a live WhatsApp transport exists.  None of those is true today, which is
intentional.

Run it:
    python execution/payment/send_payment_reminder.py
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import Settings, load_settings
from execution.payment.check_payment_status import (
    DATASET_VERIFIED,
    PaymentRecord,
    load_records,
)
from execution.storage import format_phone_for_display

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = PROJECT_ROOT / "data" / "payment_reminder_policy.json"


class ReminderSendBlocked(RuntimeError):
    """Raised whenever sending is not fully approved and possible."""


class PolicyError(RuntimeError):
    """Raised when the reminder policy file is missing or malformed."""


@dataclass(frozen=True)
class PlannedReminder:
    account_ref: str
    customer_name: str
    customer_phone: str
    stage: str
    days_overdue: int
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "account_ref": self.account_ref,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "stage": self.stage,
            "days_overdue": self.days_overdue,
            "message": self.message,
        }


@dataclass
class ReminderPlan:
    as_of: date
    dataset_kind: str
    reminders: list[PlannedReminder] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)


def load_policy(path: Path | str | None = None) -> dict[str, Any]:
    policy_path = Path(path) if path else DEFAULT_POLICY_PATH
    if not policy_path.is_file():
        raise PolicyError(f"Reminder policy not found at {policy_path}")
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PolicyError(f"{policy_path} is not valid JSON: {exc}") from exc
    for key in (
        "first_reminder_days_after_due",
        "min_days_between_reminders",
        "max_reminders_per_account",
        "templates",
    ):
        if key not in policy:
            raise PolicyError(f"Reminder policy is missing '{key}'")
    return policy


def _template_for(policy: dict[str, Any], stage: str) -> str:
    for template in policy.get("templates", []):
        if template.get("stage") == stage:
            return str(template.get("body", ""))
    raise PolicyError(f"No reminder template defined for stage '{stage}'")


def _stage_for(policy: dict[str, Any], reminders_sent: int) -> str:
    stages = [template.get("stage") for template in policy.get("templates", [])]
    if not stages:
        raise PolicyError("Reminder policy defines no template stages")
    index = min(reminders_sent, len(stages) - 1)
    return str(stages[index])


def _blocking_reason(
    record: PaymentRecord,
    policy: dict[str, Any],
    today: date,
) -> str | None:
    """Why this account must NOT get a reminder today (None = it is due)."""
    if record.dispute_open or record.invoice_status == "disputed":
        return "open dispute - must go to a human first"
    if record.do_not_remind:
        return "customer asked reminders to stop"
    if not record.is_outstanding:
        return "no outstanding balance"
    if record.reminders_sent >= int(policy["max_reminders_per_account"]):
        return "maximum reminders for this account already reached"
    try:
        due = date.fromisoformat(record.due_date)
    except ValueError:
        return "due date missing or invalid"
    days_overdue = (today - due).days
    if days_overdue < int(policy["first_reminder_days_after_due"]):
        return "not yet past the first reminder interval"
    if record.last_reminder_date:
        try:
            last = date.fromisoformat(record.last_reminder_date)
        except ValueError:
            return "last reminder date invalid"
        if today - last < timedelta(days=int(policy["min_days_between_reminders"])):
            return "too soon since the last reminder"
    return None


def plan_reminders(
    records: list[PaymentRecord],
    policy: dict[str, Any],
    *,
    today: date | None = None,
    dataset_kind: str = "fictional",
) -> ReminderPlan:
    """Decide who would be reminded today. Sends nothing, writes nothing."""
    as_of = today or date.today()
    plan = ReminderPlan(as_of=as_of, dataset_kind=dataset_kind)

    for record in records:
        reason = _blocking_reason(record, policy, as_of)
        if reason:
            plan.skipped.append({"account_ref": record.account_ref, "reason": reason})
            continue

        stage = _stage_for(policy, record.reminders_sent)
        days_overdue = (as_of - date.fromisoformat(record.due_date)).days
        template = _template_for(policy, stage)
        message = (
            template.replace("{customer_name}", record.customer_name)
            .replace("{business_name}", str(policy.get("business_name", "Last Honor Funerals")))
            .replace("{amount}", record.balance_display)
            .replace("{due_date}", record.due_date)
            .replace("{phone}", format_phone_for_display(record.customer_phone))
        )
        plan.reminders.append(
            PlannedReminder(
                account_ref=record.account_ref,
                customer_name=record.customer_name,
                customer_phone=record.customer_phone,
                stage=stage,
                days_overdue=days_overdue,
                message=message,
            )
        )
    return plan


def send_reminders(
    plan: ReminderPlan,
    policy: dict[str, Any],
    settings: Settings | None = None,
    *,
    confirm_send: bool = False,
) -> list[dict[str, Any]]:
    """Always refuses for now. Kept as the single gate for future sending."""
    settings = settings or load_settings()

    blockers: list[str] = []
    if not confirm_send:
        blockers.append("--confirm-send was not given")
    if not settings.payment_reminders_enabled:
        blockers.append("PAYMENT_REMINDERS_ENABLED is false in configuration")
    if policy.get("status") != "approved":
        blockers.append(f"reminder policy status is {policy.get('status')!r}, not 'approved'")
    if not policy.get("approved_by_owner"):
        blockers.append("the business owner has not approved the reminder policy")
    if not policy.get("templates_approved"):
        blockers.append("the message templates have not been approved")
    if plan.dataset_kind != DATASET_VERIFIED:
        blockers.append(
            f"payment data is {plan.dataset_kind!r}; verified payment records are required"
        )
    blockers.append("no live WhatsApp transport is built or configured yet (Phase 6)")

    raise ReminderSendBlocked(
        "Nothing was sent. Missing:\n" + "\n".join(f"  - {item}" for item in blockers)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan payment reminders (never sends).")
    parser.add_argument("--records", help="path to a payment records JSON file")
    parser.add_argument("--policy", help="path to a reminder policy JSON file")
    parser.add_argument("--today", help="pretend today is YYYY-MM-DD (for testing)")
    args = parser.parse_args(argv)

    today = date.fromisoformat(args.today) if args.today else date.today()
    policy = load_policy(args.policy)
    dataset_kind, records = load_records(args.records)
    plan = plan_reminders(records, policy, today=today, dataset_kind=dataset_kind)

    print("=" * 74)
    print("PAYMENT REMINDER PLAN - SIMULATION ONLY - NOTHING WILL BE SENT")
    print(f"policy:     {policy.get('policy_id')} (status: {policy.get('status')})")
    print(f"data:       {dataset_kind} ({len(records)} records)")
    print(f"as of:      {plan.as_of.isoformat()}")
    print("=" * 74)

    if plan.reminders:
        print(f"\n{len(plan.reminders)} reminder(s) WOULD be due:\n")
        for reminder in plan.reminders:
            print(f"  [{reminder.stage}] {reminder.account_ref} "
                  f"({reminder.customer_name}, {reminder.days_overdue} days overdue)")
            print(f"    to: {format_phone_for_display(reminder.customer_phone)}")
            for line in reminder.message.splitlines():
                print(f"    | {line}")
            print("")
    else:
        print("\nNo reminders would be due today.")

    if plan.skipped:
        print("Skipped accounts:")
        for item in plan.skipped:
            print(f"  - {item['account_ref']}: {item['reason']}")

    try:
        send_reminders(plan, policy, confirm_send=False)
    except ReminderSendBlocked as exc:
        print("")
        print(exc)

    print("")
    print("Reminder history was NOT written, because no reminder was sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
