
import secrets
from datetime import datetime, timezone

import jwt


def create_jwt(username: str, secret_hex: str) -> str:
    """Create an HS512-signed JWT for the given username."""

    now = datetime.now(timezone.utc)

    claims = {
        "iat": int(now.timestamp()),
        "jti": secrets.token_hex(16),
        "payload": {
            "user": username,
            "date": now.date().isoformat(),
        },
    }

    secret = bytes.fromhex(secret_hex)

    return jwt.encode(
        claims,
        secret,
        algorithm="HS512",
    )
