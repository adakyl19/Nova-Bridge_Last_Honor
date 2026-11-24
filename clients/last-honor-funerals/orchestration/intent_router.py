"""Work out what a customer is asking, and how urgent it is.

This is deterministic, free and testable: no AI API is called.  It is the
"mock AI provider" the local prototype runs on.  When you later approve a paid
model, `ai_provider.py` is the one place that changes - this router can stay as
a fallback and as the safety net for urgent cases.

Rules are tried in priority order (death and collections first, greetings last),
which is how "my father passed away, what are your prices?" becomes a
condolence plus a human follow-up rather than a price list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

URGENCY_ROUTINE = "routine"
URGENCY_SENSITIVE = "sensitive"
URGENCY_URGENT = "urgent"

UNKNOWN_INTENT = "unknown"


@dataclass(frozen=True)
class Rule:
    intent: str
    patterns: tuple[str, ...]
    urgency: str = URGENCY_ROUTINE
    needs_human: bool = False


@dataclass(frozen=True)
class IntentResult:
    intent: str
    confidence: float
    urgency: str
    needs_human: bool
    matched: tuple[str, ...] = field(default_factory=tuple)
    secondary: tuple[str, ...] = field(default_factory=tuple)


# --------------------------------------------------------------------------
# Rule table. Order = priority (the earlier rule wins a tie).
# --------------------------------------------------------------------------
RULES: tuple[Rule, ...] = (
    Rule(
        "death_notification",
        (
            r"\bpassed (away|on)\b",
            r"\bmy late\b",
            r"\bdied\b",
            r"\bdeath\b",
            r"\bdeceased\b",
            r"\bbereave\w*\b",
            r"\bjust lost\b",
            r"\blost (my|our) (father|mother|dad|mom|mum|son|daughter|wife|husband|child|baby|brother|sister|grandmother|grandfather|friend|relative)\b",
            r"\bfuneral (is|for)\b",
        ),
        urgency=URGENCY_SENSITIVE,
        needs_human=True,
    ),
    Rule(
        "collection_request",
        (
            r"\bcollections?\b",
            r"\bcollect (the |my |him|her|them|his)\b",
            r"\b(mortuary|hearse)\b",
            r"\b(pick up|fetch|transport|move|bring)\b.{0,25}\b(body|remains|corpse|deceased)\b",
        ),
        urgency=URGENCY_URGENT,
        needs_human=True,
    ),
    Rule(
        "payment_dispute",
        (
            r"\bdisput\w+\b",
            r"\bwrong (amount|balance)\b",
            r"\bnot my (account|balance)\b",
            r"\bi don'?t owe\b",
            r"\bovercharg\w*\b",
            r"\bincorrect (amount|balance)\b",
        ),
        urgency=URGENCY_SENSITIVE,
        needs_human=True,
    ),
    Rule(
        "payment_arrangement",
        (
            r"\bpayment arrangement",
            r"\barrangements? to pay\b",
            r"\bpay(ing)? (in|it in) (instalments?|installments?|parts)\b",
            r"\binstalments?\b",
            r"\binstallments?\b",
            r"\bcan i pay (later|next|month|at the end)\b",
            r"\bextension\b",
            r"\bcan'?t afford\b",
            r"\bstruggling to pay\b",
            r"\bmake a plan to pay\b",
        ),
        urgency=URGENCY_SENSITIVE,
        needs_human=True,
    ),
    Rule(
        "payment_claim_paid",
        (
            r"\bi (have |already )?paid\b",
            r"\bpayment (was|has been) made\b",
            r"\bproof of payment\b",
            r"\bi made (the |a )?payment\b",
            r"\bmoney (was|has been) (paid|transferred|sent)\b",
            r"\beft\b",
            r"\bdeposited (the )?(money|payment)\b",
        ),
        urgency=URGENCY_SENSITIVE,
        needs_human=True,
    ),
    Rule(
        "payment_stop_reminders",
        (
            r"\bstop (sending|the)( me| us)? (reminders|messages|sms)\b",
            r"\bstop (the )?reminders\b",
            r"\bstop\b.{0,15}\breminders?\b",
            r"\bremove me from\b",
            r"\bdon'?t (message|contact|whatsapp) me\b",
            r"\bunsubscribe\b",
            r"\bno more (reminders|messages)\b",
            r"\bstop messaging\b",
        ),
        urgency=URGENCY_SENSITIVE,
        needs_human=True,
    ),
    Rule(
        "payment_balance_query",
        (
            r"\bbalance\b",
            r"\boutstanding\b",
            r"\bowe\b",
            r"\bstatement\b",
            r"\baccount balance\b",
            r"\bhow much (do i|must i|should i) (still )?(owe|pay)\b",
            r"\bmy account\b",
        ),
        urgency=URGENCY_SENSITIVE,
        needs_human=True,
    ),
    Rule(
        "complaint",
        (
            r"\bangry\b",
            r"\bfurious\b",
            r"\bupset\b",
            r"\bdisappointed\b",
            r"\bterrible\b",
            r"\bunacceptable\b",
            r"\bappalling\b",
            r"\bridiculous\b",
            r"\buseless\b",
            r"\bcomplain\w*\b",
            r"\bno one (has |have )?(called|responded|helped)\b",
            r"\bstill waiting\b",
            r"\bpoor service\b",
            r"\bnot happy\b",
            r"\bfed up\b",
            r"\bfrustrat\w+\b",
        ),
        urgency=URGENCY_SENSITIVE,
        needs_human=True,
    ),
    Rule(
        "human_handoff",
        (
            r"\b(speak|talk|chat) (to|with)\b.{0,25}\b(human|person|someone|somebody|staff|manager|agent|consultant|team)\b",
            r"\breal person\b",
            r"\bhuman\b",
            r"\bmanager\b",
            r"\bstaff member\b",
            r"\boperator\b",
        ),
        needs_human=True,
    ),
    Rule(
        "callback_request",
        (
            r"\bcall ?back\b",
            r"\bcallback\b",
            r"\bcall me\b",
            r"\bphone me\b",
            r"\bring me\b",
            r"\bcontact me\b",
            r"\bget back to me\b",
            r"\breturn my call\b",
        ),
        needs_human=True,
    ),
    Rule(
        "funeral_arrangements",
        (
            r"\barrange\w*\b",
            r"\bfuneral (service|plan)\b",
            r"\bburial\b",
            r"\bcremat\w+\b",
            r"\bmemorial\b",
            r"\bcoffin\b",
            r"\bcasket\b",
            r"\bgrave\w*\b",
            r"\btombstone\b",
            r"\bprogramme\b",
            r"\bprogram\b",
            r"\bwake\b",
            r"\bviewing\b",
        ),
        needs_human=True,
    ),
    Rule(
        "pricing",
        (
            r"\bprices?\b",
            r"\bpricing\b",
            r"\bcosts?\b",
            r"\bhow much\b",
            r"\bquote\b",
            r"\bquotation\b",
            r"\bfees?\b",
            r"\bcharge\w*\b",
            r"\bafford\w*\b",
            r"\bexpensive\b",
            r"\bcheap\w*\b",
            r"\bpay for\b",
        ),
    ),
    Rule(
        "services",
        (
            r"\bservices?\b",
            r"\bpackages?\b",
            r"\boptions\b",
            r"\bwhat do you (offer|provide|do)\b",
            r"\btypes? of funeral\b",
        ),
    ),
    Rule(
        "opening_hours",
        (
            r"\bhours?\b",
            r"\bopen\b",
            r"\bclosed\b",
            r"\bopening\b",
            r"\bwhat time\b",
            r"\bweekend\b",
            r"\bsunday\b",
            r"\bsaturday\b",
            r"\b24\s?hours?\b",
            r"\bavailable (today|tomorrow|now)\b",
        ),
    ),
    Rule(
        "address",
        (
            r"\baddress\b",
            r"\bwhere are you\b",
            r"\blocation\b",
            r"\blocated\b",
            r"\bdirections?\b",
            r"\bfind you\b",
            r"\bbranch\b",
            r"\boffice\b",
            r"\bpremises\b",
            r"\bsuburb\b",
        ),
    ),
    Rule(
        "contact_details",
        (
            r"\bphone number\b",
            r"\bcontact (number|details)\b",
            r"\btelephone\b",
            r"\bemail\b",
            r"\bwhatsapp number\b",
            r"\byour number\b",
        ),
    ),
    Rule(
        "greeting",
        (
            r"^(hi|hello|hey|hallo|good (morning|afternoon|evening)|morning|afternoon|evening)\b",
            r"^(howzit|sawubona|dumela|molo|shalom)\b",
        ),
    ),
    Rule(
        "thanks",
        (
            r"\bthank (you|u)\b",
            r"\bthanks\b",
            r"\bappreciate\b",
            r"\bgrateful\b",
        ),
    ),
    Rule(
        "goodbye",
        (
            r"\bgoodbye\b",
            r"\bbye\b",
            r"\bsee you\b",
            r"\bgood night\b",
        ),
    ),
    Rule(
        "general_help",
        (
            r"\bhelp\b",
            r"\bassist\w*\b",
            r"\benquir\w+\b",
            r"\binquir\w+\b",
            r"\bquestion\b",
            r"\binformation\b",
        ),
    ),
)

_COMPILED: tuple[tuple[int, Rule, tuple[re.Pattern[str], ...]], ...] = tuple(
    (index, rule, tuple(re.compile(pattern, re.IGNORECASE) for pattern in rule.patterns))
    for index, rule in enumerate(RULES)
)


def route(message: str) -> IntentResult:
    """Classify one message. Never raises on odd input."""
    text = (message or "").strip()
    if not text:
        return IntentResult(
            intent="invalid",
            confidence=0.0,
            urgency=URGENCY_ROUTINE,
            needs_human=False,
        )

    scored: list[tuple[int, int, Rule, tuple[str, ...]]] = []
    for index, rule, patterns in _COMPILED:
        matched = tuple(pattern.pattern for pattern in patterns if pattern.search(text))
        if matched:
            scored.append((len(matched), index, rule, matched))

    if not scored:
        return IntentResult(
            intent=UNKNOWN_INTENT,
            confidence=0.25,
            urgency=URGENCY_ROUTINE,
            needs_human=True,
        )

    # Most matching signals wins; ties go to the earlier (higher priority) rule.
    scored.sort(key=lambda item: (-item[0], item[1]))
    hits, _, primary, matched = scored[0]
    secondary = tuple(
        rule.intent for _, _, rule, _ in scored[1:4] if rule.intent != primary.intent
    )

    return IntentResult(
        intent=primary.intent,
        confidence=min(0.95, 0.45 + 0.15 * hits),
        urgency=primary.urgency,
        needs_human=primary.needs_human,
        matched=matched,
        secondary=secondary,
    )
