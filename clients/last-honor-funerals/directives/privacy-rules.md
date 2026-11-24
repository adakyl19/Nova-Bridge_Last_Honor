# DIRECTIVE: Privacy and data handling

**Layer:** Directive
**Used by:** `execution/log_enquiry.py`, `execution/create_callback_request.py`, `execution/storage.py`
**Status:** working rules; POPIA alignment to be confirmed with the owner

## Purpose

Protect grieving families' personal information while still giving staff what
they need to help. South Africa's Protection of Personal Information Act
(POPIA) applies to this data; the business owner remains the responsible party.

## Inputs

- Customer messages.
- Name and phone number offered by the customer.
- Generated replies.
- Business facts (not personal information).

## Expected outputs

- Logs that contain only what is needed.
- ID numbers, passport numbers and banking details redacted before storage.
- Replies that never expose one customer's information to another.

## What we collect, and why

| Data | Why | Where it is stored |
| --- | --- | --- |
| Name | so staff know who to ask for | `callback_requests.jsonl`, `escalations.jsonl`, `enquiries.jsonl` |
| Phone number (WhatsApp / typed) | so staff can call back | same |
| The customer's message (redacted) | so staff have context | `enquiries.jsonl`, `conversation_log.jsonl` |
| Intent, urgency, escalation reason | so the team can prioritise | `enquiries.jsonl`, `escalations.jsonl` |

## What we never collect

- ID numbers, passport numbers, bank account or card numbers.
- Medical records, diagnoses, or cause of death.
- Proof of relationship or family documents.
- Home addresses of living family members (unless needed for a collection, and
  then only as part of the message text).
- Anything about a third party who is not part of the request.

## Rules

1. If a message contains a 13–19 digit number or a labelled ID/passport/bank
   detail, it is redacted before logging, and the customer is told not to send
   such details on WhatsApp.
2. A reply must never include another person's name, number, balance or
   arrangement.
3. Never send a customer's details to a third party, group or external tool
   that has not been approved.
4. Never post customer data in a public channel, issue tracker or chat.
5. Access to `data/runtime/` is staff-only; the folder is git-ignored.
6. Data may only be used for the enquiry that created it. No marketing reuse.
7. When the real system goes live, define a retention period with the owner and
   delete old records on schedule (not implemented yet — see roadmap).

## Restrictions

- Do not ask "for our records" — ask only when a detail is needed to help.
- Do not confirm that a person is a customer, or that they owe money, to
  anyone other than the verified account holder via staff.
- Do not store WhatsApp access tokens, API keys or session data in the
  repository. Only `.env` (git-ignored) or the hosting provider's secret store.
- Do not enable verbose logging that dumps full message bodies outside the
  protected data folder.

## Edge cases

| Situation | Handling |
| --- | --- |
| Customer sends an ID number | Reply with the privacy note; log shows `[redacted]`; do not ask for it again. |
| Customer sends a photo of an ID document | Phase 6 will need a rule for attachments; for now reply asking them not to send documents and offer a human. |
| Someone asks about another family's funeral | Do not confirm or deny; escalate to staff. |
| Customer asks "what do you have on me?" | Escalate; staff handle data requests. |
| Wrong number / not a customer | Reply politely; do not reveal any record exists. |
| Customer asks for their data to be deleted | Record the request as an escalation; a person handles deletion. |

## Escalation conditions

Escalate any request to access, correct or delete personal information, any
suspected impersonation, and any message that appears to come from someone
other than the customer.

## Open questions for the owner

- Who may access the WhatsApp inbox and the data folder?
- What retention period is appropriate (e.g. 12 months after the account closes)?
- Where should the information officer's contact details be published?
