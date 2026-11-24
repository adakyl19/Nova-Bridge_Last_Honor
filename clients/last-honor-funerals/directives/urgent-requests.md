# DIRECTIVE: Urgent and sensitive requests

**Layer:** Directive
**Used by:** `orchestration/intent_router.py` (urgency), `orchestration/receptionist_brain.py` (priority)
**Status:** working rules; after-hours procedure unknown

## Purpose

Make sure the messages that cannot wait are treated differently from a
question about opening hours — without ever claiming that help has already
arrived.

## Inputs

- The customer's message.
- Classified intent and urgency.
- `emergency_procedure` from the approved profile, if verified.

## Expected outputs

- Urgency set to `urgent` or `sensitive`.
- Priority `urgent` or `high` on the escalation record.
- A short reply that is calm, direct and free of promises.
- A staff alert, with the true delivery result reflected in the wording.

## What counts as urgent

| Level | Signals |
| --- | --- |
| `urgent` | collection or transport of the deceased; mortuary; "come now"; "we don't know what to do"; a body being kept somewhere unsuitable; any risk to a living person |
| `sensitive` | a death has just happened; a complaint or anger; a payment dispute; a family conflict; a request to stop reminders after a loss |
| `routine` | price questions, hours, address, callbacks, general enquiries |

## Rules

1. Urgent means **the escalation and alert happen first**, before lengthy
   conversation. Asking for a name and number is the only thing that may come
   before it.
2. Do not slow an urgent request down with questions that are not needed to
   act: no budget, no ID number, no medical details.
3. Give at most one practical instruction. If `emergency_procedure` is
   verified, use it; otherwise say a team member must speak to them.
4. Never say "stay calm", "don't worry", or "everything will be fine".
5. If the customer describes immediate danger to a person, tell them to contact
   emergency services (10111 / 112) — this is general safety, not business
   advice — and still escalate.
6. Tone for urgent replies: shorter sentences, no small talk, condolence first
   if a death is involved.

## Restrictions

- Do not promise a time of arrival, a collection, or a call-back time.
- Do not suggest the family move or transport the deceased themselves.
- Do not give medical, legal or religious instructions.
- Do not ask for the cause of death.
- Do not treat a message as non-urgent because the customer is calm or polite.

## Edge cases

| Situation | Handling |
| --- | --- |
| "My mother passed away at the hospital, can you fetch her?" | Condolences; urgent collection escalation; ask name, number, hospital/suburb. |
| "There is a body at the house and it is very hot" | Urgent; escalate immediately; ask name and number; offer emergency-services guidance if there is any risk. |
| Customer is angry and mentions a death | Complaint + death; condolence first, then escalate as `high` with both reasons in the summary. |
| Customer types in capitals or with many messages | Do not comment on tone; answer the content. |
| "It's not urgent, but..." | Still classify by content, not by the customer's label. |
| After-hours message (no verified procedure) | Say a team member must contact them and that we cannot confirm after-hours availability. Never claim the office is open. |
| Customer gives no contact number in an urgent case | Keep the escalation, note the missing detail, still reply. |

## Escalation conditions

Every urgent or sensitive message creates an escalation. An urgent escalation
must not be deduplicated away by a later routine message in the same
conversation — the urgent record stays open until a person closes it.
