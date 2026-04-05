from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app

MAGIC_LINK_SALT = "magic-link-auth"
MAGIC_LINK_MAX_AGE = 900  # 15 minutes


def generate_magic_token(email: str) -> str:
    """Generate a signed, time-limited token encoding the given email address."""
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps(email, salt=MAGIC_LINK_SALT)


def verify_magic_token(token: str) -> str | None:
    """Verify and decode a magic link token.

    Returns the email string on success, or None if expired or invalid.
    """
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = s.loads(token, salt=MAGIC_LINK_SALT, max_age=MAGIC_LINK_MAX_AGE)
        return email
    except (SignatureExpired, BadSignature):
        return None
