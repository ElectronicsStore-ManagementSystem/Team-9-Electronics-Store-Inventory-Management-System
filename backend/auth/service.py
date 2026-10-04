import hashlib, hmac, secrets, time

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${digest}"

def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$", 1)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return hmac.compare_digest(candidate, digest)

def has_role(user_role: str, allowed_roles: set[str]) -> bool:
    return user_role in allowed_roles

def session_expired(last_activity: float, timeout_seconds: int = 900) -> bool:
    return time.time() - last_activity >= timeout_seconds
