"""Look up a customer's account status - read only, fictional data only.

IMPORTANT: Last Honor Funerals' real payment system is not known yet.  This
module reads `data/payment_records.sample.json`, which is marked as fictional.
The lookup therefore reports `sample_only`, and `assert_verified_dataset()`
refuses to let anything operate on it as if it were real.

The receptionist itself never calls this module: payment questions are handed
to the accounts team (see directives/payment-reminders.md).  This exists so the
data shape and the verification logic can be designed and tested before the
real source is connected.

Run it to see the shape:
    python execution/payment/check_payment_status.py --phone 082 000 0001
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.storage import normalise_phone

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RECORDS_PATH = PROJECT_ROOT / "data" / "payment_records.sample.json"

DATASET_FICTIONAL = "fictional"
DATASET_VERIFIED = "verified"


class PaymentDataNotAvailable(RuntimeError):
    """Raised when real, verified payment data is required but not available."""


@dataclass(frozen=True)
class PaymentRecord:
    account_ref: str
    customer_name: str
    customer_phone: str
    balance_cents: int
    currency: str
    due_date: str
    invoice_status: str
    do_not_remind: bool = False
    dispute_open: bool = False
    reminders_sent: int = 0
    last_reminder_date: str | None = None

    @property
    def balance_display(self) -> str:
        return f"{self.currency} {self.balance_cents / 100:,.2f}"

    @property
    def is_outstanding(self) -> bool:
        return self.invoice_status == "outstanding" and self.balance_cents > 0


@dataclass(frozen=True)
class PaymentLookup:
    """The answer to "what does the system know about this customer's account?"."""

    status: str  # sample_only | not_found | unavailable | invalid
    record: PaymentRecord | None
    message: str

    @property
    def usable_with_customer(self) -> bool:
        """False unless the data is real and verified."""
        return False


def load_records(path: Path | str | None = None) -> tuple[str, list[PaymentRecord]]:
    """Return (dataset_kind, records)."""
    record_path = Path(path) if path else DEFAULT_RECORDS_PATH
    if not record_path.is_file():
        return ("missing", [])
    try:
        raw = json.loads(record_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PaymentDataNotAvailable(f"{record_path} is not valid JSON: {exc}") from exc

    dataset_kind = str(raw.get("dataset_kind", "unknown")).lower()
    records: list[PaymentRecord] = []
    for entry in raw.get("records", []):
        try:
            records.append(
                PaymentRecord(
                    account_ref=str(entry["account_ref"]),
                    customer_name=str(entry["customer_name"]),
                    customer_phone=normalise_phone(str(entry.get("customer_phone", ""))) or "",
                    balance_cents=int(entry.get("balance_cents", 0)),
                    currency=str(entry.get("currency", "ZAR")),
                    due_date=str(entry.get("due_date", "")),
                    invoice_status=str(entry.get("invoice_status", "outstanding")),
                    do_not_remind=bool(entry.get("do_not_remind", False)),
                    dispute_open=bool(entry.get("dispute_open", False)),
                    reminders_sent=int(entry.get("reminders_sent", 0)),
                    last_reminder_date=entry.get("last_reminder_date"),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return (dataset_kind, records)


def assert_verified_dataset(dataset_kind: str) -> None:
    """Stop anything that needs real data from running on fictional records."""
    if dataset_kind != DATASET_VERIFIED:
        raise PaymentDataNotAvailable(
            f"Payment data is '{dataset_kind}', not '{DATASET_VERIFIED}'. Last Honor "
            "Funerals' real payment source is not connected yet, so no balance may be "
            "shown, discussed or acted on."
        )


def check_payment_status(
    *,
    phone: str | None = None,
    account_ref: str | None = None,
    records_path: Path | str | None = None,
) -> PaymentLookup:
    """Read-only lookup. Never writes, never decides anything financial."""
    if not phone and not account_ref:
        return PaymentLookup("invalid", None, "Provide a phone number or an account reference.")

    dataset_kind, records = load_records(records_path)
    if dataset_kind == "missing":
        return PaymentLookup("unavailable", None, "No payment records file is available.")

    wanted_phone = normalise_phone(phone) if phone else None
    wanted_ref = (account_ref or "").strip().upper()

    for record in records:
        if wanted_ref and record.account_ref.upper() == wanted_ref:
            return PaymentLookup(
                "sample_only" if dataset_kind != DATASET_VERIFIED else "found",
                record,
                "Fictional test record - must never be shown to a real customer.",
            )
        if wanted_phone and record.customer_phone == wanted_phone:
            return PaymentLookup(
                "sample_only" if dataset_kind != DATASET_VERIFIED else "found",
                record,
                "Fictional test record - must never be shown to a real customer.",
            )

    return PaymentLookup("not_found", None, "No matching test record.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only payment status lookup (test data).")
    parser.add_argument("--phone", help="customer phone, e.g. 082 000 0001")
    parser.add_argument("--account", help="account reference, e.g. LHF-TEST-0001")
    parser.add_argument("--records", help="path to a records JSON file")
    args = parser.parse_args(argv)

    dataset_kind, records = load_records(args.records)
    print("=" * 74)
    print("PAYMENT LOOKUP - FICTIONAL TEST DATA ONLY")
    print(f"dataset_kind: {dataset_kind}   records loaded: {len(records)}")
    print("This is not connected to any real payment system and must not be used")
    print("to tell a real customer anything about money.")
    print("=" * 74)

    lookup = check_payment_status(
        phone=args.phone, account_ref=args.account, records_path=args.records
    )
    print(f"status: {lookup.status}")
    print(f"note:   {lookup.message}")
    if lookup.record:
        record = lookup.record
        print("")
        print(f"  account_ref:   {record.account_ref}")
        print(f"  customer:      {record.customer_name} (fictional)")
        print(f"  phone:         {record.customer_phone}")
        print(f"  balance:       {record.balance_display}")
        print(f"  due_date:      {record.due_date}")
        print(f"  status:        {record.invoice_status}")
        print(f"  do_not_remind: {record.do_not_remind}")
        print(f"  dispute_open:  {record.dispute_open}")
        print(f"  reminders sent: {record.reminders_sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
