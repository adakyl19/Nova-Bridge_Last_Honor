"""Central configuration for the Last Honor Funerals receptionist.

Everything the rest of the code needs to know about "where am I running and
what is switched on" lives here.  Values come from environment variables, and
optionally from a local `.env` file (parsed without any third-party package so
the prototype runs on a clean Python install).

Safety defaults are deliberate:
- the AI provider is the free, local "mock" provider;
- messages are printed to the console, not sent to WhatsApp;
- payment reminders are switched off.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# The folder that contains config.py == the last-honor-funerals project root.
PROJECT_ROOT = Path(__file__).resolve().parent


def _parse_dotenv(path: Path) -> None:
    """Copy KEY=VALUE lines from a .env file into the environment.

    Real environment variables win: an existing value is never overwritten, so
    a temporary override on the command line still works.
    """
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _path(name: str, fallback: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return fallback
    candidate = Path(raw).expanduser()
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


@dataclass(frozen=True)
class Settings:
    """A snapshot of the configuration, passed around explicitly.

    Passing settings around (instead of reading environment variables deep
    inside functions) is what lets the tests point the whole system at a
    throw-away data folder.
    """

    ai_provider: str = "mock"
    enable_live_ai: bool = False
    openai_api_key: str = ""
    openai_model: str = ""

    message_transport: str = "console"

    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""

    staff_alert_email: str = ""

    payment_reminders_enabled: bool = False

    data_dir: Path = PROJECT_ROOT / "data" / "runtime"
    business_profile_path: Path = PROJECT_ROOT / "data" / "business_profile.json"

    @property
    def simulation_mode(self) -> bool:
        """True while replies are printed locally instead of sent to WhatsApp."""
        return self.message_transport.strip().lower() != "whatsapp"


def load_settings(dotenv_path: Path | None = None) -> Settings:
    """Build a Settings object from the environment (+ .env if present)."""
    _parse_dotenv(PROJECT_ROOT / ".env" if dotenv_path is None else dotenv_path)

    return Settings(
        ai_provider=os.environ.get("AI_PROVIDER", "mock").strip() or "mock",
        enable_live_ai=_flag("ENABLE_LIVE_AI"),
        openai_api_key=os.environ.get("OPENAI_API_KEY", "").strip(),
        openai_model=os.environ.get("OPENAI_MODEL", "").strip(),
        message_transport=os.environ.get("MESSAGE_TRANSPORT", "console").strip() or "console",
        whatsapp_access_token=os.environ.get("WHATSAPP_ACCESS_TOKEN", "").strip(),
        whatsapp_phone_number_id=os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip(),
        whatsapp_verify_token=os.environ.get("WHATSAPP_VERIFY_TOKEN", "").strip(),
        staff_alert_email=os.environ.get("STAFF_ALERT_EMAIL", "").strip(),
        payment_reminders_enabled=_flag("PAYMENT_REMINDERS_ENABLED"),
        data_dir=_path("LH_DATA_DIR", PROJECT_ROOT / "data" / "runtime"),
        business_profile_path=_path(
            "LH_BUSINESS_PROFILE", PROJECT_ROOT / "data" / "business_profile.json"
        ),
    )
