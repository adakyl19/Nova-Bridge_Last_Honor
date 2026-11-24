"""Pull a customer's name and phone number out of a WhatsApp message.

We only collect what the team needs to call the family back.  Extraction is
deliberately conservative: if we are not fairly sure a word is a name, we
prefer to ask again rather than save "fine thanks" as a customer name.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.storage import contains_sensitive_details, normalise_phone

_WORD = r"[A-Za-z][A-Za-z'\-]{1,24}"

_NAME_PATTERNS = (
    re.compile(rf"\bmy name is\s+({_WORD}(?:\s+{_WORD}){{0,2}})", re.IGNORECASE),
    re.compile(rf"\bmy name'?s\s+({_WORD}(?:\s+{_WORD}){{0,2}})", re.IGNORECASE),
    re.compile(rf"\b(?:i am|i'm)\s+({_WORD}(?:\s+{_WORD}){{0,2}})", re.IGNORECASE),
    re.compile(rf"\bthis is\s+({_WORD}(?:\s+{_WORD}){{0,2}})", re.IGNORECASE),
    re.compile(rf"\bname\s*[:\-]\s*({_WORD}(?:\s+{_WORD}){{0,2}})", re.IGNORECASE),
)

# Words that mean "this is not a name".
_NOT_A_NAME = {
    "fine", "okay", "ok", "good", "well", "here", "there", "sorry", "calling",
    "looking", "trying", "interested", "struggling", "worried", "afraid", "busy",
    "still", "waiting", "going", "just", "really", "also", "very", "so", "not",
    "happy", "sad", "upset", "angry", "unable", "able", "asking", "enquiring",
    "inquiring", "the", "a", "an", "my", "his", "her", "their", "our", "your",
    "please", "from", "at", "and", "but", "because", "writing", "messaging",
}

# A name phrase stops at these words.
_STOP_TOKENS = {
    "and", "my", "our", "his", "her", "their", "your", "number", "cell",
    "phone", "contact", "call", "please", "from", "at", "on", "is", "was",
    "number:", "whatsapp", "email",
}

# Words that show the message is a sentence, not a bare name.
_SENTENCE_MARKERS = {
    "call", "me", "us", "on", "at", "is", "my", "please", "number",
    "email", "phone", "thanks", "thank", "you", "yes", "no", "not", "i",
    "want", "need", "give", "know", "can", "could", "would", "will",
    "speak", "talk", "ask", "asking", "sorry", "help",
}

_SA_PHONE = re.compile(r"(?:\+27|0)[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{4}\b")
_INTL_PHONE = re.compile(r"\+\d{9,15}\b")


@dataclass(frozen=True)
class CustomerDetails:
    name: str | None
    phone: str | None
    had_sensitive_details: bool

    @property
    def any(self) -> bool:
        return bool(self.name or self.phone)


def extract_name(text: str) -> str | None:
    for pattern in _NAME_PATTERNS:
        match = pattern.search(text or "")
        if not match:
            continue
        words: list[str] = []
        for word in match.group(1).split():
            if word.lower().strip(".,:-") in _STOP_TOKENS:
                break
            words.append(word.strip(".,:-"))
        cleaned = " ".join(words).strip()
        if not cleaned:
            continue
        lowered = {word.lower() for word in words}
        if lowered & _NOT_A_NAME:
            continue
        if len(cleaned) < 2:
            continue
        return cleaned
    return None


def extract_bare_name(text: str) -> str | None:
    """Read a name from a bare reply, e.g. "Thandi Mokoena, 082 555 1234".

    Only used when we have just asked for the customer's name, and only when
    the message is short and free of sentence words - otherwise we ask again
    rather than save something like "Call me on" as a customer name.
    """
    tokens = re.findall(r"[A-Za-z][A-Za-z'\-]*", text or "")
    if not tokens or len(tokens) > 6:
        return None

    words: list[str] = []
    for token in tokens[:3]:
        lowered = token.lower()
        if lowered in _SENTENCE_MARKERS or lowered in _NOT_A_NAME or lowered in _STOP_TOKENS:
            return None
        words.append(token)

    candidate = " ".join(words).strip()
    return candidate if len(candidate) >= 2 else None


def extract_phone(text: str) -> str | None:
    source = text or ""
    for pattern in (_SA_PHONE, _INTL_PHONE):
        for match in pattern.finditer(source):
            normalised = normalise_phone(match.group(0))
            if normalised:
                return normalised
    return None


def extract_details(text: str, *, expect_name: bool = False) -> CustomerDetails:
    """Name, phone, and whether the message contained ID/banking details."""
    name = extract_name(text)
    if name is None and expect_name:
        name = extract_bare_name(text)
    return CustomerDetails(
        name=name,
        phone=extract_phone(text),
        had_sensitive_details=contains_sensitive_details(text or ""),
    )
