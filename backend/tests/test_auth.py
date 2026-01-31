import pytest
from app.core.security import create_access_token, verify_access_token

def test_create_token():
    token = create_access_token(data={"sub": "testuser"})
    assert token
    assert isinstance(token, str)

def test_verify_token():
    token = create_access_token(data={"sub": "testuser"})
    payload = verify_access_token(token)
    assert payload["sub"] == "testuser"

def test_verify_invalid_token():
    with pytest.raises(Exception):
        verify_access_token("invalid.token.here")
