# Last Honor Funerals - Business Profile (working copy)

> **Status: NOT APPROVED.** Every fact below is a placeholder. The receptionist
> will not state any of it to a customer until the owner confirms it and it is
> marked `verified` in `business_profile.json`.

## Where the truth lives

`data/business_profile.json` is the single source of truth. The receptionist
reads only that file (through `execution/read_business_profile.py`). This
Markdown file is the human-friendly version for the owner to review and fill in.

## Business

| Item | Value |
| --- | --- |
| Business name | Last Honor Funerals |
| Country | South Africa |
| Address | `[BUSINESS_ADDRESS]` |
| Telephone | `[BUSINESS_PHONE]` |
| WhatsApp number | `[WHATSAPP_NUMBER]` |
| Email | `[BUSINESS_EMAIL]` |
| Opening hours | `[OPENING_HOURS]` |
| Service area | `[SERVICE_AREA]` |
| After-hours / emergency | `[EMERGENCY_PROCEDURE]` |

## Services and prices

| Item | Value |
| --- | --- |
| Approved services | `[APPROVED_SERVICES]` |
| Approved prices / quoting method | `[APPROVED_PRICES]` |
| Payment methods | `[PAYMENT_METHODS]` |
| Collection procedure | `[COLLECTION_PROCEDURE]` |
| Staff contact for alerts | `[STAFF_CONTACT]` |

## Questions the owner must answer before go-live

1. What is the physical address, and may customers visit without an appointment?
2. Which telephone number should customers call, and is it answered after hours?
3. What are the office hours, including weekends and public holidays?
4. What services and packages may the receptionist describe, in the owner's own words?
5. May prices be given on WhatsApp at all, or should every price query go to staff?
6. How should a family request a collection, and who is called first?
7. Which towns/suburbs are served?
8. Who receives urgent alerts, on which number or app, and what is the response promise?
9. What is the emergency/after-hours procedure?
10. Which payment methods are approved, and may balances ever be discussed on WhatsApp?

## How to approve a fact

1. Get the answer from the owner in writing.
2. Open `data/business_profile.json`.
3. Put the confirmed answer in that field's `value`.
4. Change that field's `status` from `unverified` to `verified`.
5. Run `python execution/read_business_profile.py` to confirm it shows as verified.
6. Only set `meta.profile_approved` to `true` once every field is confirmed.
