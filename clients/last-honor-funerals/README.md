# Last Honor Funerals — WhatsApp AI Receptionist

A WhatsApp receptionist for a South African funeral parlour, plus a **separate,
not-yet-active** payment reminder module.

Built by Nova Bridge Solutions. This README is the map: what works, what is
simulated, what is planned, and what you must decide before anything goes live.

> **Current status: local prototype.**
> No WhatsApp account, no AI API, no hosting, no paid service. The whole thing
> runs offline on the Python standard library.

---

## 1. Quick start (Windows)

Open a terminal in this folder (`clients/last-honor-funerals`):

```bat
python run_local_chat.py
```

You will see `Customer:`. Type a message and press Enter. Useful commands:
`/trace` (show what the system decided), `/reset` (start as a new customer),
`/quit`.

One-off message:

```bat
python run_local_chat.py --message "My father passed away this morning" --trace
```

See which business facts are still missing:

```bat
python execution/read_business_profile.py
```

Run the tests:

```bat
python -m unittest discover -s testing/automated_tests -t . -v
```

Nothing needs `pip install`. Python 3.10+ is required (3.12 was used here).

---

## 2. What works, what is simulated, what is planned

| Area | Status | Detail |
| --- | --- | --- |
| Intent recognition | **Working** | Rule-based, offline, 20 intents, priority ordered |
| Reply wording | **Working (mock provider)** | Scripted, compassionate, honest about what it does not know |
| Business facts | **Working, no facts yet** | 12 placeholders; nothing is stated until verified |
| Enquiry / conversation logging | **Working** | Append-only JSONL in `data/runtime/` |
| Callback requests | **Working** | Validated name + South African phone number |
| Escalation records | **Working** | Reason, priority, summary, status `open` |
| Staff notification | **Simulated** | Writes to a local "staff inbox" file. No person is alerted |
| WhatsApp send/receive | **Parsing only** | Webhook JSON parser written and tested; no network calls |
| Live AI model | **Not included** | Setting one stops with an explanation, no cost incurred |
| Payment reminders | **Design + dry-run only** | Sending is blocked by code |
| Hosting / deployment | **Not done** | Nothing is deployed anywhere |

The console says `LOCAL SIMULATION` for a reason: the system never claims a
message reached WhatsApp, or that staff were alerted, unless that is true.

---

## 3. Project structure

```
last-honor-funerals/
├── run_local_chat.py            entry point: chat in the terminal
├── config.py                    all settings in one place (.env aware)
├── directives/                  WHAT to do, in plain Markdown
│   ├── receptionist.md          tone, honesty rules, edge cases
│   ├── business-profile.md      which facts may be stated, and how they are verified
│   ├── enquiry-handling.md      intent map and answering rules
│   ├── funeral-arrangements.md  condolences, collections, arrangements
│   ├── urgent-requests.md       urgency levels and urgent behaviour
│   ├── human-escalation.md      the three things never to confuse
│   ├── privacy-rules.md         what is collected, redacted and never stored
│   └── payment-reminders.md     future module rules (switched off)
├── orchestration/               HOW the AI decides
│   ├── receptionist_brain.py    one message in → one careful reply out
│   ├── intent_router.py         intent + urgency classification
│   ├── response_builder.py      the actual words
│   ├── detail_extractor.py      name / phone / sensitive-detail detection
│   ├── ai_provider.py           the single place a live model would plug in
│   └── models.py                Session, TurnActions, TurnResult
├── execution/                   WHAT actually happens (deterministic)
│   ├── receive_message.py       local input + WhatsApp webhook parsing
│   ├── send_message.py          console / file transports; WhatsApp refuses politely
│   ├── read_business_profile.py the only source of business facts
│   ├── log_enquiry.py           transcript, enquiry and escalation records
│   ├── create_callback_request.py
│   ├── notify_staff.py          simulated staff alert with honest result
│   ├── storage.py               JSONL storage, phone normalising, redaction
│   └── payment/
│       ├── check_payment_status.py   read-only lookup, fictional data only
│       └── send_payment_reminder.py  builds a plan, refuses to send
├── data/
│   ├── business_profile.json    the facts (all unverified placeholders)
│   ├── sample_business_profile.md  human-readable copy + owner questions
│   ├── payment_records.sample.json fictional test accounts
│   └── payment_reminder_policy.json draft intervals and templates
├── testing/
│   ├── test_cases.md            the 15 required conversations, spelled out
│   └── automated_tests/         44 passing tests, standard library only
├── docs/phase-1-report.md       the architecture report
├── .env.example                 copy to .env, never commit .env
├── .gitignore
└── requirements.txt             no packages required
```

---

## 4. How it works (the DOE architecture)

Three layers, each with one job. This is what keeps the product reliable: the
AI never directly performs actions, and the scripts never decide policy.

```
   DIRECTIVE  (directives/*.md)
   "What must happen, and what must never happen"
                    │
                    ▼
   ORCHESTRATION  (orchestration/*)
   "Understand → decide → choose the words"
                    │  calls
                    ▼
   EXECUTION  (execution/*)
   "Deterministic actions: record, validate, notify, send"
```

For one incoming WhatsApp message:

```
1. receive_message      normalise the WhatsApp payload into IncomingMessage
2. detail_extractor     read name / phone if offered; detect ID numbers
3. intent_router        intent + urgency + "needs a human?"
4. receptionist_brain   decide: answer, record, escalate, or ask for details
5. execution calls      create_callback_request / log_escalation / notify_staff
6. response_builder     wording that matches what really happened
7. log_enquiry          write the turn + delivery result
8. send_message         console / file / (future) WhatsApp
```

Why this shape:

- **Testable.** Intent routing and wording can be tested without a phone or an
  API key. 44 tests run in under a second.
- **Auditable.** Every decision leaves a record: intent, urgency, escalation
  id, notification result.
- **Swappable.** A paid model replaces `intent_router` / `response_builder`
  behind the same interfaces. The deterministic scripts stay.
- **Safe.** The AI cannot send a payment reminder, invent a price, or mark an
  escalation as handled: no code path exists for those.

---

## 5. Safety rules that are enforced in code

| Rule | Where |
| --- | --- |
| Placeholders never reach a customer | `read_business_profile.Fact.is_available` |
| No price, balance or due date is ever generated | `response_builder` has no numbers; payment intents escalate |
| "Staff alerted" only when delivery really succeeded | `notify_staff` result → `_alert_sentence` |
| Escalation ≠ notification ≠ response | `escalations.jsonl` + notification result + `status: open` |
| ID / banking details are not stored | `storage.redact_sensitive` before every log write |
| Callback needs a valid phone number | `create_callback_request` raises `ValidationError` |
| No duplicate escalation spam | `Session.escalations` dedupe per conversation |
| Payment sending impossible | `send_reminders` raises `ReminderSendBlocked` |
| No live AI by accident | `ai_provider.get_intent_provider` raises with a clear message |
| No fake WhatsApp connection | `send_message.get_transport("whatsapp")` raises |

---

## 6. Updating business information

You never edit Python to change a business fact.

1. Open `data/business_profile.json`.
2. Put the owner's confirmed answer in `value`.
3. Change that field's `status` from `unverified` to `verified`.
4. Run `python execution/read_business_profile.py` to check it.
5. Only set `meta.profile_approved` to `true` when everything is confirmed.

A field marked `verified` that still holds its placeholder is treated as
**unverified**, so a half-finished edit cannot leak to a customer.

Current state: **12 of 12 facts unverified**, so the receptionist offers a human
for every business question. That is intentional, not a bug.

The ten questions the owner must answer are listed in
`data/sample_business_profile.md`.

---

## 7. Data and privacy

- Runtime records live in `data/runtime/` and are **git-ignored**.
- Message text is redacted (13–19 digit numbers, labelled ID / passport / bank
  details) before it is written.
- Conversations are in memory only: restarting the program forgets the
  conversation, but the transcript stays on disk.
- POPIA: the business owner remains the responsible party. Retention, access
  and the information officer must still be agreed — see
  `directives/privacy-rules.md`.

Files written at runtime: `conversation_log.jsonl`, `enquiries.jsonl`,
`callback_requests.jsonl`, `escalations.jsonl`, `staff_notifications.jsonl`,
`outbox.jsonl`.

---

## 8. Payment reminders (separate module, switched off)

The parlour's payment system is **unknown**, so nothing assumes a system.

- `data/payment_records.sample.json` holds five clearly fictional accounts.
- `check_payment_status.py` looks them up read-only and marks every result
  `sample_only`; `assert_verified_dataset()` refuses fictional data.
- `send_payment_reminder.py` prints the reminders that *would* go out, the
  reason each other account is skipped, and everything still missing before
  sending.
- The receptionist never looks up a balance. Every money question becomes an
  accounts escalation.

Try it:

```bat
python execution/payment/send_payment_reminder.py
python execution/payment/check_payment_status.py --phone "082 000 0001"
```

Before this module can send anything, the owner must approve: the data source,
the intervals, the templates, who verifies payments, the stop process, and the
dispute process. See `directives/payment-reminders.md`.

---

## 9. Tests

```bat
python -m unittest discover -s testing/automated_tests -t . -v
```

44 tests: the 15 required conversations, safety invariants, business-profile
rules, WhatsApp payload parsing, and the payment module's refusals. All pass.

`testing/test_cases.md` documents each conversation and what must never happen.
Manual review items (tone with the owner, alert destination, POPIA review) are
listed there too.

---

## 10. Roadmap

| Phase | Status |
| --- | --- |
| 1. Inspect and plan | Done — see `docs/phase-1-report.md` |
| 2. Directives | Done — eight directives, placeholders marked |
| 3. Local receptionist | Done — 20 intents, mock provider, logging, escalation |
| 4. Execution layer | Done — validated, tested, deterministic |
| 5. Payment reminder design | Done — plan + policy + refusal to send |
| 6. WhatsApp integration | **Not started** — needs Meta Business, a test number, webhooks, approval |
| 7. Production readiness | **Not started** — needs owner sign-off on every fact and process |

Nothing in phases 6–7 happens without your explicit approval and a budget
conversation.

---

## 11. Known limitations

- Conversations are held in memory, so a restart loses context (records remain).
- Only text messages are handled; images, voice notes and documents are ignored
  by the webhook parser.
- Intent routing is keyword-based. It handles the required cases well and will
  misread unusual phrasing; those become "unknown" and are escalated rather than
  guessed.
- Staff alerting is a local file. There is no email, SMS or WhatsApp alert yet.
- There is no admin interface. Records are JSONL files, inspected by hand.
- The reminder policy is a draft; the amounts in the fictional templates are
  test data.

---

## 12. Missing reference material

`reference-framework/` from the original brief is **not present** in this
workspace, so nothing from it was reused. If you want the original
`read_sheet.py`, `append_to_sheet.py` or `update_sheet.py` considered later,
place those three files (plus `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`) in
`reference-framework/` and they will be reviewed before any reuse.

They are not needed for Module A: business facts live in one JSON file and no
spreadsheet is involved.

---

## 13. Decisions needed from Last Honor Funerals

1. Address, telephone, email, WhatsApp number.
2. Opening hours, including weekends and after-hours policy.
3. Approved services and packages, in the owner's words.
4. Whether any price may be given on WhatsApp, and the approved price list.
5. Collection procedure and who handles collections.
6. Who receives urgent alerts, on which channel.
7. Emergency / after-hours procedure and service area.
8. Payment methods (and later: the payment system, intervals, templates).
9. POPIA: retention period, who may access records, information officer.

Everything else can be built while these are outstanding — the receptionist
simply offers a human instead of guessing.
