# DIRECTIVE: Funeral arrangement and collection requests

**Layer:** Directive
**Used by:** `orchestration/receptionist_brain.py`, `orchestration/response_builder.py`
**Status:** working rules; procedure details still unknown

## Purpose

Meet a family at the hardest moment with kindness, capture only what the
arrangements team needs to call them back, and never imply that a funeral,
collection or booking is already arranged.

## Inputs

- The customer's message.
- Name and contact number (asked for, or already known).
- Town or suburb, if the customer offers it.
- `collection_procedure` and `emergency_procedure` from the approved profile.

## Expected outputs

1. Condolences, in the customer's own words where possible.
2. A clear statement of what has been recorded.
3. A request for the minimum details needed.
4. An escalation marked `urgent` (collection) or `high` (arrangements).
5. A callback request once a valid name and number are known.

## Rules

### Opening

- If a death is mentioned: "I'm very sorry for your loss. We're here to help
  you through the next steps."
- Do not ask "How can I help?" straight after a death. Offer help first.

### What to collect

| Request | Ask for | Do not ask for |
| --- | --- | --- |
| Collection | name, best number, town/suburb where the loved one is | cause of death, ID number, medical history |
| Arrangements | name, best number, what the family would like to discuss | budget, banking details, family disputes |
| General help | name, best number | anything else |

One message, one request. If a detail is already known, do not ask again.

### Recording

- Record the request with `create_callback_request` only when the name and a
  usable phone number are both present.
- If either is missing, ask for it; never create a half-record.
- A collection request is urgency `urgent`; arrangements are urgency `high`.

## Restrictions

- Never say a collection is "on its way", "booked", "confirmed" or "scheduled".
- Never confirm a date, time, venue, price, coffin choice or payment.
- Never advise on legal, medical or religious requirements.
- Never state a procedure that is not in the approved profile. If
  `collection_procedure` is unverified, say a team member will explain the
  process.
- Never ask where the family lives unless it is needed for a collection.

## Edge cases

| Situation | Handling |
| --- | --- |
| Death reported with no details | Condolences + ask for name and number; escalation still created. |
| Family gives a name but no number | Thank them, ask only for the number. |
| Family gives a number but no name | Ask only for the name. |
| Death happened long ago, family is planning ahead | Still `death_notification`; arrangements team follows up. |
| Collection from a hospital, home and mortuary in one message | Record all of it in the message text; ask once for name, number and location. |
| Customer is a neighbour or friend, not family | Help the same way; do not ask for proof of relationship. |
| Request outside the service area | Do not refuse or accept; escalate and let staff decide. |
| Family asks "can you come now?" | Do not promise. Say it has been marked urgent and the team needs to contact them immediately. |
| Two deaths in the family | One escalation; note it in the summary. |

## Escalation conditions

Always escalate:

- every death notification;
- every collection, transport or mortuary request (priority `urgent`);
- every funeral arrangement request;
- any question about procedures, timelines, documents, or costs.

Never escalate a request that is purely logistical and already answered by
verified profile data (e.g. "what is your address?" when the address is
verified).
