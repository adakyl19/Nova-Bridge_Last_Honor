# DIRECTIVE: Human escalation

**Layer:** Directive
**Used by:** `orchestration/receptionist_brain.py`, `execution/notify_staff.py`
**Status:** working rules; staff contact details and response promises are still unknown

## Purpose

Make sure a person at Last Honor Funerals picks up anything the receptionist
must not handle alone, and make sure the customer is never told something about
staff that is not true.

## Inputs

- Classified intent and urgency.
- Customer name and phone number, if given.
- Whether the approved business profile can answer the question.
- The result of the actual staff-alert attempt.

## Expected outputs

For an escalating message, three separate artefacts:

1. **An escalation record** in `data/runtime/escalations.jsonl` with reason,
   priority, summary, customer details, status `open`, and the customer's
   redacted message.
2. **A staff alert** via `notify_staff`, whose `ok` / `simulated` values are
   returned honestly.
3. **A reply** whose wording matches the real notification result.

## The three things that must never be confused

| Fact | Where it is stored | How we know |
| --- | --- | --- |
| An escalation was created | `escalations.jsonl` | the file write succeeded |
| An alert reached staff | notification result | `ok=true` and `simulated=false` |
| A staff member responded | a person updates the record | never set by code |

The receptionist may say "I've recorded your message for our team" whenever (1)
is true. It may say "I've alerted our team" **only** when (2) is true and not
simulated. It may **never** say anything about (3).

## Rules

### Escalate immediately when the customer

- reports a death or a recent loss;
- needs a collection, transport, or the deceased fetched from a hospital, home
  or mortuary;
- wants to arrange or change a funeral, burial, cremation, viewing or wake;
- complains, is angry, or reports that nobody has responded;
- asks for a human, a manager, or a specific staff member;
- asks anything that is not covered by approved business information;
- raises money: a balance, a payment made, a dispute, an arrangement, or a
  request to stop reminders;
- describes an emergency, a safety risk, or a body being kept somewhere
  unsuitable.

### Priority

| Priority | Meaning | Examples |
| --- | --- | --- |
| `urgent` | Needs attention now | collection request, emergency procedure |
| `high` | Needs a person today | death notification, complaint, payment dispute |
| `normal` | Needs a person soon | price question, callback request, general question |

### Deduplication

Repeating the same matter in one conversation reuses the existing escalation
(`Session.escalations`) instead of alerting staff twice. The repeat message is
still recorded in the enquiry and conversation logs.

### Callback requests

If both a name and a usable phone number are known, a callback request record is
created (`callback_requests.jsonl`) and the alert points at it. Without both,
the receptionist asks for the missing detail and does not invent one.

## Restrictions

- Do not promise a response time. There is no agreed service level yet.
- Do not say "someone is on their way", "we will be there in an hour", or "the
  manager has seen this".
- Do not mark an escalation as resolved, assigned or handled.
- Do not put another customer's name or details into an alert or a reply.
- Do not send an alert to a number or address that the owner has not approved.
- Do not escalate a greeting, a thank-you or a polite goodbye.

## Edge cases

| Situation | Handling |
| --- | --- |
| Customer refuses to give a name or number | Record the escalation with what exists; do not block help. Note in the summary that contact details are missing. |
| Customer gives a number that is not valid | Ask once more politely. Do not store an unusable number as if it were valid. |
| Two urgent matters in one message ("my mother passed and we can't pay") | Primary intent decides the reply; note both in the summary. |
| Alert delivery is simulated (local mode) | Say the message was recorded for the team — never that staff were alerted. |
| Alert delivery failed (e.g. email configured but unavailable) | Say it was recorded but the alert could not be confirmed, and ask the customer to phone if urgent. |
| Customer says "don't worry, sorted" | Do not close the escalation; only a person may. Reply kindly and leave the record open. |
| Same customer sends the same message five times | Record the turns; create one escalation; send one alert. |

## Escalation conditions

Escalation is **mandatory** for every item in the Rules list above. Escalation
is **forbidden** for: greetings, thanks, verifying a fact already recorded in
the conversation, and questions answerable from verified profile data.

## Open questions for the owner

- Who receives urgent alerts, and on which channel?
- Is there an after-hours number, and who answers it?
- What response time may the receptionist promise, if any?
- Should alerts go to one person or a group?
