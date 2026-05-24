from cryptography.fernet import Fernet, InvalidToken
from typing import Optional

from app.core.config import settings


class TokenCryptoError(ValueError):
    pass


def _get_fernet() -> Fernet:
    key = settings.TOKEN_ENCRYPTION_KEY.strip()
    if not key:
        raise TokenCryptoError("TOKEN_ENCRYPTION_KEY is required for Gmail connections.")
    try:
        return Fernet(key.encode("utf-8"))
    except ValueError as exc:
        raise TokenCryptoError("TOKEN_ENCRYPTION_KEY must be a valid Fernet key.") from exc


def encrypt_token(token: str) -> str:
    if not token:
        return ""
    return _get_fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: Optional[str]) -> Optional[str]:
    if not encrypted_token:
        return None
    try:
        return _get_fernet().decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise TokenCryptoError("Stored Gmail token could not be decrypted.") from exc
