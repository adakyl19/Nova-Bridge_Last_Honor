# DIRECTIVE: Customer enquiry handling

**Layer:** Directive
**Used by:** `orchestration/intent_router.py`, `orchestration/receptionist_brain.py`
**Status:** working rules

## Purpose

Turn a plain WhatsApp message into a clear, safe next step: answer it from
approved information, or hand it to a person with what they need to help.

## Inputs

- The customer's message.
- The conversation so far (name, number, previous intent).
- `data/business_profile.json` (approved facts only).

## Expected outputs

1. One classified intent with an urgency level.
2. Either an approved answer, or an escalation with a documented reason.
3. A contact record when a follow-up is needed and the details are known.
4. A logged turn in `enquiries.jsonl` and `conversation_log.jsonl`.

## Intent map

| Intent | Example | Answer source | Needs a human? |
| --- | --- | --- | --- |
| greeting | "Hi" | script | no |
| address | "Where are you?" | profile `address` | only if unverified |
| opening_hours | "Are you open Sunday?" | profile `opening_hours` | only if unverified |
| services | "What packages do you have?" | profile `services` | only if unverified |
| pricing | "How much is a funeral?" | profile `prices` | always until prices approved |
| contact_details | "What's your number?" | profile `phone` | only if unverified |
| death_notification | "My father passed away" | script + escalation | yes |
| collection_request | "Can you collect the body?" | script + escalation | yes, urgent |
| funeral_arrangements | "I want to arrange a funeral" | script + escalation | yes |
| callback_request | "Please call me" | script + escalation | yes |
| human_handoff | "I want to talk to a person" | script + escalation | yes |
| complaint | "No one has called me back" | script + escalation | yes |
| payment_* | "How much do I owe?" | escalation only | yes |
| unknown | anything else | honest "I don't have a confirmed answer" | yes |

## Rules

- Classify the **most serious** intent first. A message that mentions a death
  and a price is a death notification with a price question attached.
- If a question cannot be answered from verified profile data, say so in one
  sentence, then offer a human. Never pad with general knowledge.
- Ask for contact details only when a human follow-up is needed.
- One question at a time. If the customer already gave a detail, do not ask
  again.
- When an answer is available, give it plainly and stop. No upsell, no extra
  questions.
- Record every turn. A receptionist that cannot show what it told a family is
  not usable in a real business.

## Restrictions

- No invented facts, no comparisons with other funeral parlours, no advice
  outside the business's scope.
- No promises about availability, timing, discounts or arrangements.
- Do not discuss amounts, invoices, statements or account numbers.
- Do not reuse a customer's message for marketing.

## Edge cases

| Situation | Handling |
| --- | --- |
| Two questions in one message | Answer the primary; mention that the team will cover the other. |
| Question about a service not in the profile | Treat as `unknown`; escalate. |
| Customer asks "are you a bot?" | Answer honestly and offer a person. |
| Customer asks about a different branch or town | If `service_area` is unverified, escalate rather than guess. |
| Customer asks "how much is a coffin only?" | Still a price question: never estimate; escalate. |
| Customer sends only a location pin/photo | Phase 6 will handle attachments; for now ask them to type it. |
| Repeat of the same question | Reuse the open escalation; do not alert staff twice. |

## Escalation conditions

Follow `human-escalation.md`. Every `unknown` answer and every unverified
information request creates an escalation with reason
`unanswered_information_request`.
