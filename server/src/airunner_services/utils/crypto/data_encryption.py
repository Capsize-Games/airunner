from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Optional

from cryptography.fernet import Fernet, InvalidToken


class DataEncryptionError(RuntimeError):
    pass


def _parse_keys(raw: str) -> list[bytes]:
    keys: list[bytes] = []
    for part in (raw or "").split(","):
        key = part.strip()
        if not key:
            continue
        try:
            keys.append(key.encode("utf-8"))
        except Exception:
            continue
    return keys


def generate_fernet_key() -> str:
    """Return a new base64 Fernet key as a string."""
    return Fernet.generate_key().decode("utf-8")


@dataclass(frozen=True)
class Keyring:
    encrypt_key: bytes
    decrypt_keys: tuple[bytes, ...]

    def fernet_for_encrypt(self) -> Fernet:
        return Fernet(self.encrypt_key)

    def fernet_for_decrypt(self) -> Iterable[Fernet]:
        for k in self.decrypt_keys:
            yield Fernet(k)


def get_keyring(required: bool = True) -> Optional[Keyring]:
    """Build a keyring from env.

    Env:
      - AIRUNNER_DATA_ENCRYPTION_KEYS: comma-separated Fernet keys (first used for encrypt).

    If required=True and no keys are present, raises.
    """
    raw = (os.environ.get("AIRUNNER_DATA_ENCRYPTION_KEYS") or "").strip()
    keys = _parse_keys(raw)
    if not keys:
        if required:
            raise DataEncryptionError(
                "AIRUNNER_DATA_ENCRYPTION_KEYS is not set; refusing to store encrypted user data"
            )
        return None

    # First key is used for encrypt; all keys can decrypt.
    return Keyring(encrypt_key=keys[0], decrypt_keys=tuple(keys))


def encrypt_bytes(data: bytes) -> bytes:
    if data is None:
        raise DataEncryptionError("encrypt_bytes received None")
    keyring = get_keyring(required=True)
    assert keyring is not None
    return keyring.fernet_for_encrypt().encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    if token is None:
        raise DataEncryptionError("decrypt_bytes received None")
    keyring = get_keyring(required=True)
    assert keyring is not None

    last_err: Exception | None = None
    for f in keyring.fernet_for_decrypt():
        try:
            return f.decrypt(token)
        except InvalidToken as exc:
            last_err = exc
            continue

    raise DataEncryptionError(
        "Failed to decrypt payload with provided keys"
    ) from last_err
