from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qsl

from cryptography.fernet import Fernet, InvalidToken


class SecurityError(ValueError):
    pass


def _fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class TokenCipher:
    def __init__(self, secret: str):
        self._fernet = Fernet(_fernet_key(secret))

    def encrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise SecurityError("Unable to decrypt protected value") from exc


def sign_payload(payload: dict[str, Any], secret: str, ttl: timedelta) -> str:
    body = payload | {"iat": datetime.now(timezone.utc).timestamp(), "ttl": ttl.total_seconds()}
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()
    return ".".join(
        (
            base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("="),
            base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("="),
        )
    )


def verify_signed_payload(token: str, secret: str) -> dict[str, Any]:
    try:
        encoded_body, encoded_signature = token.split(".", 1)
    except ValueError as exc:
        raise SecurityError("Malformed signed payload") from exc

    padded_body = encoded_body + "=" * (-len(encoded_body) % 4)
    padded_signature = encoded_signature + "=" * (-len(encoded_signature) % 4)
    raw = base64.urlsafe_b64decode(padded_body.encode("utf-8"))
    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()
    actual = base64.urlsafe_b64decode(padded_signature.encode("utf-8"))
    if not hmac.compare_digest(expected, actual):
        raise SecurityError("Invalid payload signature")

    payload = json.loads(raw.decode("utf-8"))
    issued_at = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
    ttl = timedelta(seconds=payload["ttl"])
    if datetime.now(timezone.utc) > issued_at + ttl:
        raise SecurityError("Signed payload expired")
    return payload


def build_session_token(user_id: int, secret: str) -> str:
    return sign_payload({"sub": user_id, "kind": "session"}, secret, timedelta(days=7))


def read_session_token(token: str, secret: str) -> int:
    payload = verify_signed_payload(token, secret)
    if payload.get("kind") != "session":
        raise SecurityError("Unexpected session token kind")
    return int(payload["sub"])


def build_oauth_state(user_id: int, provider: str, secret: str) -> str:
    return sign_payload({"sub": user_id, "provider": provider, "kind": "oauth-state"}, secret, timedelta(minutes=15))


def read_oauth_state(token: str, secret: str) -> dict[str, Any]:
    payload = verify_signed_payload(token, secret)
    if payload.get("kind") != "oauth-state":
        raise SecurityError("Unexpected oauth state kind")
    return payload


@dataclass(slots=True)
class TelegramInitData:
    raw: str
    user: dict[str, Any]
    auth_date: datetime
    query_id: str | None


def validate_telegram_init_data(raw_init_data: str, bot_token: str, max_age_seconds: int) -> TelegramInitData:
    if not raw_init_data:
        raise SecurityError("Telegram init data is empty")

    params = dict(parse_qsl(raw_init_data, keep_blank_values=True))
    received_hash = params.pop("hash", None)
    if not received_hash:
        raise SecurityError("Telegram init data is missing hash")

    secret = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    data_check_string = "\n".join(f"{key}={params[key]}" for key in sorted(params))
    calculated_hash = hmac.new(secret, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise SecurityError("Telegram init data hash mismatch")

    auth_date = datetime.fromtimestamp(int(params["auth_date"]), tz=timezone.utc)
    if datetime.now(timezone.utc) - auth_date > timedelta(seconds=max_age_seconds):
        raise SecurityError("Telegram init data expired")

    user_payload = json.loads(params["user"])
    return TelegramInitData(
        raw=raw_init_data,
        user=user_payload,
        auth_date=auth_date,
        query_id=params.get("query_id"),
    )
