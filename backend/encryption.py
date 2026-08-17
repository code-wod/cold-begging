import base64

from cryptography.fernet import Fernet, InvalidToken

from .config import FERNET_KEY


def _fernet():
    key = FERNET_KEY.encode()
    if len(key) != 44:
        key = base64.urlsafe_b64encode(key)
    return Fernet(key)


def encrypt_plaintext(plaintext):
    if not plaintext:
        return None
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_plaintext(ciphertext):
    if not ciphertext:
        return None
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return None