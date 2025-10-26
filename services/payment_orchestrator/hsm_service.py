"""Utilities for interacting with SoftHSM via PKCS#11."""

from __future__ import annotations

import atexit
import base64
import os
import threading
from contextlib import contextmanager
from typing import Iterator

import pkcs11
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pkcs11 import Attribute, Key, KeyType, Mechanism, ObjectClass
from pkcs11.exceptions import NoSuchKey, PKCS11Error

DEFAULT_LIBRARY = "/usr/lib/softhsm/libsofthsm2.so"
SIGNING_KEY_LABEL = os.getenv("HSM_SIGNING_KEY_LABEL", "payment-signing-key")
ENCRYPTION_KEY_LABEL = os.getenv("HSM_ENCRYPTION_KEY_LABEL", "payment-encryption-key")
TOKEN_LABEL = os.getenv("SOFTHSM_TOKEN_LABEL", os.getenv("HSM_LABEL", "payment-hsm"))
USER_PIN = os.getenv("SOFTHSM_USER_PIN", os.getenv("HSM_PIN", "5678"))

_LIB = pkcs11.lib(os.getenv("SOFTHSM_MODULE", DEFAULT_LIBRARY))
_TOKEN = _LIB.get_token(token_label=TOKEN_LABEL)
_SESSION_LOCK = threading.Lock()
_SESSION: pkcs11.Session | None = None


def _open_session() -> pkcs11.Session:
    return _TOKEN.open(user_pin=USER_PIN)


def _close_session() -> None:
    global _SESSION
    session, _SESSION = _SESSION, None
    if session is not None:
        try:
            session.close()
        except PKCS11Error:
            pass


def _get_session() -> pkcs11.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = _open_session()
    return _SESSION


atexit.register(_close_session)


@contextmanager
def session_scope() -> Iterator[pkcs11.Session]:
    """Provide a shared SoftHSM session with serialized access."""
    with _SESSION_LOCK:
        session = _get_session()
        try:
            yield session
        except PKCS11Error:
            # force session reinitialisation on next use
            _close_session()
            raise


def _ensure_signing_key(session: pkcs11.Session) -> None:
    try:
        session.get_key(
            object_class=ObjectClass.PRIVATE_KEY,
            key_type=KeyType.RSA,
            label=SIGNING_KEY_LABEL,
        )
    except NoSuchKey:
        public_template = {
            Attribute.LABEL: SIGNING_KEY_LABEL,
            Attribute.TOKEN: True,
            Attribute.PUBLIC_EXPONENT: (1 << 16) + 1,
            Attribute.VERIFY: True,
        }
        private_template = {
            Attribute.LABEL: SIGNING_KEY_LABEL,
            Attribute.TOKEN: True,
            Attribute.SIGN: True,
            Attribute.EXTRACTABLE: False,
        }
        session.generate_keypair(
            KeyType.RSA,
            2048,
            public_template=public_template,
            private_template=private_template,
        )


def _ensure_encryption_key(session: pkcs11.Session) -> None:
    try:
        session.get_key(
            object_class=ObjectClass.SECRET_KEY,
            key_type=KeyType.AES,
            label=ENCRYPTION_KEY_LABEL,
        )
    except NoSuchKey:
        session.generate_key(
            KeyType.AES,
            256,
            template={
                Attribute.LABEL: ENCRYPTION_KEY_LABEL,
                Attribute.TOKEN: True,
                Attribute.ENCRYPT: True,
                Attribute.DECRYPT: True,
                Attribute.SENSITIVE: True,
                Attribute.EXTRACTABLE: False,
            },
        )


def initialize_keys_if_not_exist() -> None:
    """Ensure signing and encryption keys exist within the token."""
    with session_scope() as session:
        _ensure_signing_key(session)
        _ensure_encryption_key(session)


def _get_signing_private_key(session: pkcs11.Session) -> Key:
    return session.get_key(
        object_class=ObjectClass.PRIVATE_KEY,
        key_type=KeyType.RSA,
        label=SIGNING_KEY_LABEL,
    )


def _get_signing_public_key(session: pkcs11.Session) -> Key:
    return session.get_key(
        object_class=ObjectClass.PUBLIC_KEY,
        key_type=KeyType.RSA,
        label=SIGNING_KEY_LABEL,
    )


def _get_encryption_key(session: pkcs11.Session) -> Key:
    return session.get_key(
        object_class=ObjectClass.SECRET_KEY,
        key_type=KeyType.AES,
        label=ENCRYPTION_KEY_LABEL,
    )


def sign_message(message: str) -> bytes:
    data = message.encode("utf-8")
    with session_scope() as session:
        key = _get_signing_private_key(session)
        signature = key.sign(data, mechanism=Mechanism.SHA256_RSA_PKCS)
        return bytes(signature)


def get_public_key_der() -> bytes:
    with session_scope() as session:
        key = _get_signing_public_key(session)
        modulus = int.from_bytes(key[Attribute.MODULUS], "big")
        exponent = int.from_bytes(key[Attribute.PUBLIC_EXPONENT], "big")
    public_numbers = rsa.RSAPublicNumbers(exponent, modulus)
    public_key = public_numbers.public_key()
    return public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)


def encrypt_token(plaintext: bytes) -> str:
    with session_scope() as session:
        key = _get_encryption_key(session)
        iv = os.urandom(16)
        ciphertext = key.encrypt(
            plaintext,
            mechanism=Mechanism.AES_CBC_PAD,
            mechanism_param=iv,
        )
    blob = base64.urlsafe_b64encode(iv + bytes(ciphertext)).decode("ascii")
    return f"hsm:v1:{blob}"


def decrypt_token(token: str) -> bytes:
    if not token.startswith("hsm:v1:"):
        raise ValueError("unsupported token format")
    payload = base64.urlsafe_b64decode(token.split(":", 2)[2])
    iv, ciphertext = payload[:16], payload[16:]
    with session_scope() as session:
        key = _get_encryption_key(session)
        plaintext = key.decrypt(
            ciphertext,
            mechanism=Mechanism.AES_CBC_PAD,
            mechanism_param=iv,
        )
    return bytes(plaintext)
