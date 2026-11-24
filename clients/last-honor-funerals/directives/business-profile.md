# DIRECTIVE: Business information

**Layer:** Directive
**Data:** `data/business_profile.json` (machine-readable), `data/sample_business_profile.md` (human-readable)
**Code:** `execution/read_business_profile.py`
**Status:** **no business fact has been verified yet**

## Purpose

Guarantee that every business fact the receptionist states comes from the
owner's written approval, and that updating facts never requires changing code.

## Inputs

- `data/business_profile.json`, with one entry per fact:
  `status` (`verified` / `unverified`), `value`, `placeholder`, `description`.

## Expected outputs

- `read_business_profile.load_profile()` returns a `BusinessProfile`.
- `profile.is_available("<key>")` is the only permission to state a fact.
- `profile.value("<key>")` never returns a placeholder.
- A customer never sees a placeholder or a guess.

## The fact set

| Key | Placeholder | Used for |
| --- | --- | --- |
| `address` | `[BUSINESS_ADDRESS]` | "Where are you?" |
| `phone` | `[BUSINESS_PHONE]` | "What is your number?" |
| `whatsapp_number` | `[WHATSAPP_NUMBER]` | future WhatsApp identity |
| `email` | `[BUSINESS_EMAIL]` | email enquiries |
| `opening_hours` | `[OPENING_HOURS]` | "Are you open on Sunday?" |
| `services` | `[APPROVED_SERVICES]` | package and service questions |
| `prices` | `[APPROVED_PRICES]` | price questions |
| `collection_procedure` | `[COLLECTION_PROCEDURE]` | how a collection works |
| `payment_methods` | `[PAYMENT_METHODS]` | how families may pay |
| `staff_contact` | `[STAFF_CONTACT]` | where alerts should go |
| `emergency_procedure` | `[EMERGENCY_PROCEDURE]` | after-hours guidance |
| `service_area` | `[SERVICE_AREA]` | which towns are served |

## Rules

1. A fact is "available" only when `status == "verified"` **and** `value` is
   non-empty **and** `value` is not the placeholder.
2. False, null, empty list and placeholder values are all treated as missing.
3. If a fact is missing, the receptionist says it cannot confirm it and offers
   a human. It never fills the gap from general knowledge.
4. Prices are special: even when `prices` is verified, the receptionist may
   only repeat the approved wording. It never calculates, quotes a deposit, or
   adjusts a price.
5. Changes to business facts are made by editing the JSON file, then running
   `python execution/read_business_profile.py` to check the result.
6. Keep `meta.profile_approved` false until every field is confirmed.

## Restrictions

- Never hard-code an address, number, price, hour or staff name in Python.
- Never infer facts from the business name, country or industry.
- Never copy facts from another funeral parlour, a website or an old brochure
  without the owner's confirmation.
- Never commit real customer or staff personal information to this repository.

## Edge cases

| Situation | Handling |
| --- | --- |
| Field marked `verified` but still holds the placeholder | Treated as unverified; customer gets the honest fallback. |
| Field marked `verified` with an empty list | Treated as unverified. |
| JSON file missing or invalid | The program stops with a clear error; it does not start in a guessing mode. |
| Owner updates hours for a public holiday | Edit the value; no code change, no restart needed for the next conversation. |
| Two sources disagree | `business_profile.json` wins; delete the stale duplicate. |

## Escalation conditions

Any request for information whose fact is not available is escalated with
reason `unanswered_information_request`, so the team can answer and so the
owner can see which facts are missing.

## Required from the owner before go-live

See the ten questions in `data/sample_business_profile.md`.
