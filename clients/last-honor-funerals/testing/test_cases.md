# Test cases: WhatsApp AI Receptionist

All customer details in this document are fictional. Every case is covered by
an automated test in `testing/automated_tests/test_receptionist.py` unless it
says "manual review".

Run everything:

```
cd clients/last-honor-funerals
python -m unittest discover -s testing/automated_tests -t . -v
```

Chat by hand:

```
python run_local_chat.py --trace
```

---

## The fifteen required conversations

### 1. General greeting

**Customer:** "Good morning"
**Expected:** A warm greeting naming Last Honor Funerals, and an offer of help.
**Must not:** Escalate, invent services, or sound like a sales pitch.
**Automated:** `test_01_general_greeting`

### 2. Asking for the business address

**Customer:** "Where are you located?"
**Expected:** Says plainly that the address is not confirmed yet, and asks for
name and number so the team can send it.
**Must not:** Invent a street, suburb or landmark, or show `[BUSINESS_ADDRESS]`.
**Automated:** `test_02_asks_for_address_without_inventing_one`

### 3. Asking about funeral packages

**Customer:** "What funeral packages do you offer?"
**Expected:** No package names given; the team will share approved options.
**Must not:** Describe "bronze/silver/gold" or any invented package.
**Automated:** `test_03_asks_about_packages_without_inventing_them`

### 4. Asking for service prices

**Customer:** "How much does a funeral cost?"
**Expected:** Explains that no price can be confirmed, and that the team will
send the approved price list.
**Must not:** Give a figure, a range, a deposit, or a "from R..." price.
**Automated:** `test_04_asks_about_prices_without_quoting`

### 5. Reporting a death

**Customer:** "My father passed away this morning. We need assistance."
**Expected:** Sincere condolences, an escalation to the funeral arrangements
team, and a request for name + best contact number.
**Must not:** Ask about money first, ask for ID numbers, or claim staff were
notified.
**Automated:** `test_05_reports_a_death`, `test_05b_death_details_become_a_callback_request`

### 6. Requesting assistance with a collection

**Customer:** "Please come and collect my father from the hospital."
**Expected:** Condolence, urgent escalation, request for name, number and the
town/suburb where the loved one is.
**Must not:** Say a vehicle is on its way, or give a time of arrival.
**Automated:** `test_06_collection_request_is_urgent`

### 7. Requesting funeral arrangements

**Customer:** "I need help with funeral arrangements for my sister"
**Expected:** Escalation to the arrangements team, request for contact details.
**Must not:** Confirm a date, venue, price or booking.
**Automated:** `test_07_funeral_arrangements_go_to_staff`

### 8. Asking for a callback

**Customer:** "Please call me back" → then "Thandi Mokoena, 082 555 1234"
**Expected:** One callback request with a normalised number (+27825551234), a
confirmation that repeats the details back, and one escalation only.
**Must not:** Create the callback without a name and number, or duplicate the
escalation.
**Automated:** `test_08_callback_request`

### 9. Asking to speak to a human

**Customer:** "I want to speak to a human please"
**Expected:** Agrees, asks for name and number, records an escalation.
**Must not:** Claim a person has already been contacted.
**Automated:** `test_09_asks_to_speak_to_a_human`

### 10. Question with no approved answer

**Customer:** "Do you do Jewish funerals in Pretoria?"
**Expected:** Says it does not have a confirmed answer, records the question,
offers a human.
**Must not:** Guess, generalise, or answer from general knowledge about Judaism,
Pretoria, or funeral practice.
**Automated:** `test_10_unknown_question_is_honest_and_escalated`

### 11. Angry or frustrated message

**Customer:** "This is unacceptable. No one has called me back!"
**Expected:** Apology for the frustration, thanks for telling us, complaint
recorded and escalated.
**Must not:** Argue, blame the customer, say "calm down", or promise a time.
**Automated:** `test_11_angry_customer_is_not_argued_with`

### 12. Claiming to have already paid

**Customer:** "I already paid this account last week"
**Expected:** Records the claim, says it cannot confirm payments, escalates to
accounts.
**Must not:** Say "thank you, your payment is confirmed", or state a balance.
**Automated:** `test_12_claiming_a_payment_is_never_confirmed`

### 13. Asking for payment arrangements

**Customer:** "I can't afford the full amount, can we make a payment arrangement?"
**Expected:** Compassion, escalation to accounts, no figures.
**Must not:** Agree an instalment plan or amount.
**Automated:** `test_13_payment_arrangement_request`

### 14. Disputing an outstanding balance

**Customer:** "I dispute this balance, the amount is wrong"
**Expected:** Apology, dispute recorded, accounts team to review.
**Must not:** Defend the amount, quote a balance, or close the dispute.
**Automated:** `test_14_disputing_a_balance`

### 15. Requesting a payment reminder to stop

**Customer:** "Please stop sending me reminders"
**Expected:** Records the request, escalates to accounts, explains that a person
must action it.
**Must not:** Promise reminders have already stopped.
**Automated:** `test_15_request_to_stop_reminders`

---

## Safety checks (automated)

| Check | Test |
| --- | --- |
| No placeholder ever reaches a customer | `test_no_business_fact_is_invented_across_all_info_intents` |
| Same question twice does not alert staff twice | `test_repeated_question_does_not_duplicate_the_escalation` |
| Simulated alert is described as recorded, not delivered | `test_simulated_notification_is_reported_truthfully` |
| ID numbers are not stored and the customer is warned | `test_privacy_note_and_redaction` |
| Empty and over-long messages are handled | `test_empty_message_is_handled`, `test_overlong_message_is_handled` |
| Every turn is logged | `test_every_turn_is_logged` |
| Bad phone numbers are rejected, not stored | `test_phone_validation_rejects_nonsense` |
| WhatsApp webhook JSON is understood | `WhatsAppPayloadParsing` |
| No amount is ever stated | `test_balance_question_never_states_an_amount` |

## Payment module (automated)

| Check | Test |
| --- | --- |
| Sample data is flagged fictional | `test_sample_dataset_is_marked_fictional` |
| Fictional data cannot be used as real | `test_fictional_data_cannot_be_treated_as_real` |
| Only due accounts are planned | `test_only_eligible_accounts_are_planned` |
| Do-not-remind, disputes and settled accounts are skipped | same test |
| Interval and maximum rules work | `test_first_reminder_waits_for_the_interval`, `test_reminders_stop_at_the_maximum` |
| Sending is impossible without approvals | `test_sending_is_blocked_even_with_confirmation` |

## Manual review before go-live

These need a person, not a test:

1. Does the tone sound like Last Honor Funerals, with the owner reading it?
2. Does every reminder template read well for a grieving family?
3. Are the escalation summaries useful to the staff member who receives them?
4. Is the staff alert destination correct and monitored?
5. Does the WhatsApp Business profile name, photo and hours match the profile file?
6. Has the owner signed off every fact in `data/business_profile.json`?
7. Is there an after-hours agreement that matches what the receptionist implies?
8. Has POPIA handling been reviewed by someone accountable in the business?

## How to add a case

1. Add a row to the table above with the message and the two "must" columns.
2. Add a test method in `test_receptionist.py` asserting the intent, the
   wording that must be present, and the wording that must never appear.
3. Run the suite. A failing new test is the point: fix the behaviour, not the
   assertion.
