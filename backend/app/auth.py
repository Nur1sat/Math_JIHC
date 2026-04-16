from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from .config import get_settings


def hash_password(password: str, salt: str | None = None) -> str:
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_value.encode("utf-8"),
        120_000,
    )
    return f"{salt_value}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    salt, _ = password_hash.split("$", maxsplit=1)
    return hmac.compare_digest(hash_password(password, salt), password_hash)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def issue_token(user_id: int, role: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(
            (datetime.now(UTC) + timedelta(seconds=settings.token_ttl_seconds)).timestamp()
        ),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload_bytes,
        digestmod=hashlib.sha256,
    ).digest()
    return f"{_b64encode(payload_bytes)}.{_b64encode(signature)}"


def decode_token(token: str) -> dict[str, int | str]:
    settings = get_settings()
    try:
        payload_segment, signature_segment = token.split(".", maxsplit=1)
        payload_bytes = _b64decode(payload_segment)
        expected_signature = hmac.new(
            settings.secret_key.encode("utf-8"),
            payload_bytes,
            digestmod=hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(expected_signature, _b64decode(signature_segment)):
            raise ValueError("invalid signature")
        payload = json.loads(payload_bytes)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc
    if int(payload["exp"]) < int(datetime.now(UTC).timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token expired",
        )
    return payload
