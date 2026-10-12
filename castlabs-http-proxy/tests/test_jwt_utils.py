
from datetime import datetime, timezone

import jwt

from app.jwt_utils import create_jwt


TEST_SECRET_HEX = "a1" * 64


def test_create_jwt_contains_expected_claims():
    token = create_jwt("alice", TEST_SECRET_HEX)

    claims = jwt.decode(
        token,
        bytes.fromhex(TEST_SECRET_HEX),
        algorithms=["HS512"],
    )

    assert claims["iat"] > 0
    assert claims["jti"]
    assert claims["payload"]["user"] == "alice"
    assert claims["payload"]["date"] == datetime.now(
        timezone.utc
    ).date().isoformat()


def test_create_jwt_generates_unique_jti():
    first = create_jwt("alice", TEST_SECRET_HEX)
    second = create_jwt("alice", TEST_SECRET_HEX)

    first_claims = jwt.decode(
        first,
        bytes.fromhex(TEST_SECRET_HEX),
        algorithms=["HS512"],
    )
    second_claims = jwt.decode(
        second,
        bytes.fromhex(TEST_SECRET_HEX),
        algorithms=["HS512"],
    )

    assert first_claims["jti"] != second_claims["jti"]
