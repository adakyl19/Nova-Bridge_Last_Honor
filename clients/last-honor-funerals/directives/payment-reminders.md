# DIRECTIVE: Payment reminders (future module — switched off)

**Layer:** Directive
**Code:** `execution/payment/check_payment_status.py`, `execution/payment/send_payment_reminder.py`
**Data:** `data/payment_records.sample.json` (fictional), `data/payment_reminder_policy.json` (draft)
**Status:** **DESIGN ONLY. Nothing sends. No real payment data exists.**

## Purpose

Define how polite, approved payment reminders will work **once** Last Honor
Funerals has told us how it records payments, and the owner has approved the
schedule and wording.

## What is true today

- The parlour's payment system is unknown. It may be a book, a spreadsheet, an
  accounting package or something else. We do not assume.
- All payment records in this repository are invented test data.
- The receptionist never looks up or states a balance. Every money question is
  escalated to a human.
- `send_payment_reminder.py` can only **plan**; sending is blocked by code.

## Inputs (future)

- Verified payment records from the parlour's real system.
- An approved reminder policy: intervals, maximum reminders, send window,
  approved templates, stop rules.
- Customer consent and the WhatsApp number on record.

## Expected outputs (future)

1. A daily list of accounts due a reminder, with the reason each other account
   was skipped.
2. Polite reminders sent only inside the approved window and schedule.
3. A reminder history record per send.
4. Automatic stop on payment, dispute, arrangement or request.
5. An escalation for every dispute, arrangement request, or claimed payment.

## Rules

### Before anything is sent

All of these must be true, in writing:

1. The real payment source is identified and read-only access is agreed.
2. The owner approves the reminder intervals (e.g. 3, 10, 21 days after due).
3. The owner approves every message template, word for word.
4. The owner approves who verifies payments and how.
5. A stop process exists and is tested.
6. A complaints/dispute process exists.
7. POPIA handling is confirmed (see `privacy-rules.md`).

### Content

- Polite, neutral, never threatening. No "final demand", no debt-collector
  tone, no mention of funeral services as leverage.
- One reminder per send window; never at night, never on a Sunday.
- Include enough for the customer to recognise the account, but never another
  person's information.
- Always include a way to say "I have paid", "I dispute this" or "I need an
  arrangement".
- Stop immediately when a payment is verified, a dispute is opened, an
  arrangement is agreed, or the customer asks.

### What the receptionist does with money talk

| Customer message | Receptionist behaviour |
| --- | --- |
| "How much do I owe?" | Cannot see balances; escalate to accounts. |
| "I already paid." | Record the claim; do not confirm payment; escalate. |
| "I can't pay the full amount." | Escalate as a payment arrangement request. |
| "This amount is wrong." | Escalate as a dispute; reminders pause. |
| "Stop sending me reminders." | Record and escalate; do not promise an instant stop. |
| "What is your banking details?" | Only if `payment_methods` is verified; otherwise escalate. Never read out account numbers from memory. |

## Restrictions

- Never invent a balance, due date, invoice number or payment.
- Never assume a payment is outstanding.
- Never confirm a payment has been received.
- Never send a reminder outside an approved policy.
- Never send the same reminder twice; the history file is the guard.
- Never send from a personal phone or an unofficial WhatsApp automation. Only
  the official WhatsApp Cloud API, on the business number.
- Never create fictional records for real customers.

## Data design (proposed)

`payment_records.sample.json` shows the shape:

| Field | Purpose |
| --- | --- |
| `account_ref` | stable reference the parlour uses |
| `customer_name`, `customer_phone` | who to message |
| `balance_cents`, `currency` | amount, in cents, never floats |
| `due_date` | when it was due |
| `invoice_status` | `outstanding`, `settled`, `disputed`, `arrangement` |
| `do_not_remind` | customer's stop request |
| `dispute_open` | pause flag |
| `reminders_sent`, `last_reminder_date` | schedule guard |

`dataset_kind` must be `verified` for real data. Anything else is treated as
fictional and blocked from customer use.

## Escalation conditions

Every dispute, arrangement request, claimed payment and stop request becomes an
accounts escalation. Reminders pause for that account until a person updates
the record.

## Edge cases

| Situation | Handling |
| --- | --- |
| Payment arrives after a reminder was queued | Verify before sending; skip if settled. |
| Customer claims payment but it is not on the statement | Pause, escalate, do not argue. |
| Two family members share a number | Only discuss with the verified account holder, via staff. |
| Wrong number reaches a stranger | Apologise, stop, flag the record. |
| Account in arrears but family is in an active funeral arrangement | Do not send reminders during an open arrangement; escalate instead. |

## Decisions the owner must make

1. Which system holds the real balances, and who keeps it current?
2. What intervals and maximum number of reminders are acceptable?
3. Exact wording of each reminder.
4. Who verifies a payment, and how fast?
5. Who handles disputes and arrangements, and within what time?
6. May reminders ever be sent to a number that is also used for a new funeral?
