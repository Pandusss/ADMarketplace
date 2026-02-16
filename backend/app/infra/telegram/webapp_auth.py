from __future__ import annotations

"""
Telegram WebApp initData validation (production).
"""

import hmac
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict
from urllib.parse import parse_qsl


@dataclass(frozen=True)
class TelegramWebAppUser:
    id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None = None
    is_premium: bool = False


class TelegramWebAppAuthError(Exception):
    """Raised when WebApp init data validation fails."""
    pass


def validate_init_data(init_data: str, bot_token: str) -> TelegramWebAppUser:
    """
    Validate initData and extract Telegram user.
    
    Args:
        init_data: The raw query string from Telegram WebApp (window.Telegram.WebApp.initData)
        bot_token: The bot token used to sign the data
        
    Returns:
        TelegramWebAppUser object if valid
        
    Raises:
        TelegramWebAppAuthError on missing data, invalid hash, or malformed user JSON.
    """

    if not init_data:
        raise TelegramWebAppAuthError("Missing initData")
    if not bot_token:
        raise TelegramWebAppAuthError("TELEGRAM_BOT_TOKEN not configured")

    try:
        # 1. Parse query string
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception as e:
        raise TelegramWebAppAuthError(f"Failed to parse initData: {e}") from e

    received_hash = pairs.get("hash")
    if not received_hash:
        raise TelegramWebAppAuthError("initData missing hash")

    # 2. Build data_check_string
    check_pairs = []
    for k in sorted(pairs.keys()):
        if k == "hash":
            continue
        check_pairs.append(f"{k}={pairs[k]}")
    
    data_check_string = "\n".join(check_pairs).encode("utf-8")

    # 3. Calculate secret key
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()

    # 4. Calculate hash
    calculated_hash = hmac.new(secret_key, data_check_string, hashlib.sha256).hexdigest()

    # 5. Compare
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramWebAppAuthError("Invalid initData hash (signature mismatch)")

    # 6. Extract user
    user_raw = pairs.get("user")
    if not user_raw:
        raise TelegramWebAppAuthError("initData missing user field")

    try:
        user_obj: Dict[str, Any] = json.loads(user_raw)
    except json.JSONDecodeError as e:
        raise TelegramWebAppAuthError("Invalid initData user JSON") from e

    uid = user_obj.get("id")
    if not isinstance(uid, int):
        raise TelegramWebAppAuthError("Invalid initData: user.id must be an integer")

    return TelegramWebAppUser(
        id=uid,
        username=user_obj.get("username"),
        first_name=user_obj.get("first_name"),
        last_name=user_obj.get("last_name"),
        language_code=user_obj.get("language_code"),
        is_premium=user_obj.get("is_premium", False)
    )
