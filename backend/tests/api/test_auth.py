import pytest
from core.security import verify_password, get_password_hash

def test_password_hashing():
    pwd = "supersecret"
    hashed = get_password_hash(pwd)
    assert verify_password(pwd, hashed)
    assert not verify_password("wrong", hashed)

def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "user@nutriguard.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_failure(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "user@nutriguard.com", "password": "wrongpassword"}
    )
    assert response.status_code == 400
