# Phase 1 report — inspection, design and first build

**Project:** Last Honor Funerals WhatsApp AI Receptionist
**Prepared by:** Nova Bridge Solutions (AI build partner)
**Date:** 24 November 2026
**Status of this report:** decisions made, work completed, and what is still blocked

---

## 1. What was inspected

The brief expected a `reference-framework/` folder containing the video's
architecture files. **That folder is not present in this workspace**, and no
GitHub access was used, as instructed. The workspace contained only a
two-line placeholder `README.md`.

So this build is based on the architecture described in the brief, not on the
video's source files. Nothing from the reference framework was copied or run.

### Reference files that are still missing

If you want them reviewed, place these in `reference-framework/`:

```
reference-framework/
├── CLAUDE.md
├── AGENTS.md
├── GEMINI.md
└── execution/
    ├── read_sheet.py
    ├── append_to_sheet.py
    └── update_sheet.py
```

Only those three scripts were named as potentially reusable. Without seeing
them, I can describe them only as "Google Sheets read/append/update" and I will
not guess at their contents, credentials handling, or side effects.

**This is not blocking.** Module A needs no spreadsheet: approved business
information lives in `data/business_profile.json`, a single file the owner can
edit. If a spreadsheet is later chosen as the source of truth (for example for
the payment module), the three scripts can be adapted then, after review.

---

## 2. How the DOEC/DOE framework works

| Layer | Question it answers | In this project | Why it matters |
| --- | --- | --- | --- |
| **D — Directive** | *What must happen, and what must never happen?* | `directives/*.md` | Policy is written by a person in plain language, reviewable by the owner, not buried in code |
| **O — Orchestration** | *What does this message mean, and what should happen next?* | `orchestration/*.py` | The AI reasons and decides; it does not act directly |
| **E — Execution** | *What actually happened?* | `execution/*.py` | Deterministic, validated, testable actions with honest results |

The critical rule: **the AI never touches the world directly.** It asks the
execution layer to record, notify or send, and it receives a result it must tell
the truth about. That is what prevents the classic failure of an AI receptionist
claiming "I've notified the team" when nothing happened.

In this codebase:

- Directives define tone, escalation triggers, privacy limits and the payment
  rules.
- Orchestration classifies the message (`intent_router.py`), decides
  (`receptionist_brain.py`) and writes the words (`response_builder.py`).
- Execution validates and records (`storage.py`, `create_callback_request.py`,
  `log_enquiry.py`), notifies (`notify_staff.py`) and delivers
  (`send_message.py`).

---

## 3. Components reused, adapted or rejected

Since the reference files are absent, the honest answer is:

| Reference component | Decision | Reason |
| --- | --- | --- |
| `read_sheet.py` | **Not used** | No verified business data in a spreadsheet; file not available to review |
| `append_to_sheet.py` | **Not used** | Same; logging is local JSONL instead |
| `update_sheet.py` | **Not used** | Highest risk of silent overwrite; not appropriate for enquiry logs |
| Lead-generation / email outreach / Upwork / video scripts | **Rejected** | Unrelated to a funeral parlour and would add risk |
| Any credentials, webhook URLs or private IDs in the framework | **Rejected outright** | Never reused; this project has no copied secrets |
| Three-layer architecture itself | **Adopted** | It is the right shape for a safety-critical receptionist |

If the scripts arrive later, the review checklist is: what it reads, what it
writes, what it overwrites, where credentials come from, what happens on
failure, and whether it can be tested offline.

---

## 4. Components built new

| File | Purpose |
| --- | --- |
| `config.py` | One settings object, `.env` aware, safe defaults |
| `orchestration/intent_router.py` | 20 intents, priority ordered, urgency levels |
| `orchestration/receptionist_brain.py` | Turn handling, escalation decisions, session state |
| `orchestration/response_builder.py` | Compassionate wording that refuses to invent |
| `orchestration/detail_extractor.py` | Name / phone extraction, sensitive-detail detection |
| `orchestration/ai_provider.py` | Single seam for a future paid model |
| `execution/receive_message.py` | Local input + WhatsApp Cloud API webhook parsing |
| `execution/send_message.py` | Console/file transports; WhatsApp refuses until built |
| `execution/read_business_profile.py` | The only source of business facts |
| `execution/log_enquiry.py` | Transcript, enquiry and escalation records |
| `execution/create_callback_request.py` | Validated callback requests |
| `execution/notify_staff.py` | Simulated staff alert with an honest result |
| `execution/storage.py` | Append-only JSONL, phone normalising, redaction |
| `execution/payment/*` | Read-only lookup and a reminder planner that cannot send |
| `directives/*.md` | Eight directives covering tone through payments |
| `data/*` | Placeholder profile, fictional payment records, draft policy |
| `testing/*` | 44 automated tests + 15 documented conversations |

---

## 5. Recommended low-cost stack

| Need | Choice now | Why | Cost |
| --- | --- | --- | --- |
| Language | Python 3.12, standard library only | Runs on your Windows machine with no installs | R0 |
| Directives | Markdown | Owner can read and correct them | R0 |
| Business facts | One JSON file | No code change to update | R0 |
| Storage | Append-only JSONL | Auditable, no database server | R0 |
| Testing | `unittest` | Built in | R0 |
| AI | Rule-based mock provider | Free, deterministic, and a safe fallback later | R0 |
| Messaging | Console now, WhatsApp Cloud API at Phase 6 | Official API only, no unofficial automation | Free tier for testing, then per-conversation pricing |
| Hosting | Not chosen yet | Decide at Phase 6 based on webhook needs | Free tier possible |
| Automation | Make — optional | Useful for scheduled reminders later, not needed for the receptionist | Free tier |
| Version control | GitHub, your existing repo | Already available | R0 |

**Deliberate decision:** no paid AI model yet. A rule-based provider handles
every required conversation, costs nothing, and makes the tests deterministic.
A paid model is justified later for unusual phrasing, not for the basics.

Any future paid component needs your approval first: API usage, hosting,
Meta verification, and the per-conversation WhatsApp charge.

---

## 6. What the first working prototype looks like

Run `python run_local_chat.py`.

```
Customer: My father passed away this morning. We need assistance.

Last Honor Funerals:
I'm very sorry for your loss. We're here to help you through the next steps.
I've recorded your message and request for assistance in our system for our
team to pick up. May I please have your name and the best contact number for
our funeral arrangements team to reach you on?

   [trace] intent=death_notification urgency=sensitive needs_human=True
   [trace] escalation=ESC-20261124-2D0024 (death_notification)
   [trace] staff_notification ok=True channel=local-staff-inbox simulated=True

Customer: My name is Thandi Mokoena and my number is 082 123 4567

Last Honor Funerals:
Thank you, Thandi Mokoena. I've recorded your details and your message for our
funeral arrangements team, and they can reach you on 082 123 4567. It's in our
system for our team to pick up.

   [trace] callback_request=CB-20261124-88F790
```

What that demonstrates:

- condolescence before anything practical;
- the death is classified as sensitive and escalated immediately;
- the reply claims only what happened ("recorded … for our team to pick up"),
  never that a person was alerted;
- the second message is recognised as the missing details, without re-asking;
- a valid callback request is written with a normalised number
  (`+27821234567`) and `urgency: high`.

A question with no approved answer behaves the same honest way:

```
Customer: How much does a funeral cost?

Last Honor Funerals:
I'm not able to give you a price I can't confirm. Funeral costs depend on the
options a family chooses, so our team will send you the approved price list.
I've recorded your request for pricing in our system for our team to pick up.
May I please have your name and the best contact number for our team to reach
you on?
```

No figure, no invented package, no false promise — and the owner can see
"request for pricing" in the escalation log, which tells them exactly which
facts are missing.

---

## 7. Verification performed

| Check | Result |
| --- | --- |
| JSON files parse | Pass (3 files) |
| All Python modules compile | Pass |
| Automated test suite | **44 tests, all pass** |
| Live console conversation | Pass (death notification + details, shown above) |
| Payment reminder planner | Pass (2 due, 3 skipped with reasons, sending blocked) |
| Payment lookup CLI | Pass (fictional data clearly labelled) |
| Business profile CLI | Pass (12 unverified fields listed) |
| WhatsApp webhook parsing | Pass (offline, with a sample payload) |
| Real WhatsApp send | **Not performed — not built** |
| Live AI call | **Not performed — not built** |
| Any deployment | **Not performed** |

---

## 8. Risks and open decisions

| Risk | Mitigation in place | Still needed |
| --- | --- | --- |
| Receptionist states a wrong fact | Facts must be `verified` to be used | Owner signs off the 12 fields |
| False claim about staff | Notification result decides wording | A real alert channel |
| Sensitive data in logs | Redaction before every write | Retention policy |
| Module B sends wrongly | Sending blocked by code and config | Owner-approved policy |
| Keyword router misses phrasing | Unmatched messages escalate, never guess | Optional paid model later |
| WhatsApp policy breach | Official API only; no unofficial automation | Meta Business setup at Phase 6 |

---

## 9. Recommended next steps

1. Walk through the 15 test conversations yourself with `run_local_chat.py`.
2. Get the ten business answers from the owner (`data/sample_business_profile.md`)
   and mark them `verified`.
3. Decide the staff alert channel (WhatsApp group, email, or SMS) — then
   `notify_staff` gets a real transport.
4. Only then start Phase 6: Meta Business, test number, webhook, credentials.
5. Keep the payment module off until the parlour's payment process is known and
   approved in writing.
