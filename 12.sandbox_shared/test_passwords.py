"""Password hash helpers for the private sandbox PoC login."""
import hashlib
import hmac
import re
import secrets


PASSWORD_HASH = re.compile(r"pbkdf2-sha256:600000:([0-9a-f]{32}):([0-9a-f]{64})")


def password_digest(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000).hex()


def hash_password(password):
    if not 12 <= len(password) <= 256:
        raise ValueError("test passwords must contain 12 to 256 characters")
    salt = secrets.token_bytes(16)
    return f"pbkdf2-sha256:600000:{salt.hex()}:{password_digest(password, salt)}"


def verify_password(password, encoded):
    if not 1 <= len(password) <= 256 or not isinstance(encoded, str):
        return False
    fields = PASSWORD_HASH.fullmatch(encoded)
    if not fields:
        return False
    salt, expected = fields.groups()
    return hmac.compare_digest(password_digest(password, bytes.fromhex(salt)), expected)
