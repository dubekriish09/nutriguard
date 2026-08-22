import pytest
from core.security import create_access_token
from models.user import User

def get_token(client, email, password):
    res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    return res.json()["access_token"]

def test_admin_simulator_requires_auth(client):
    res = client.post("/api/v1/admin/rules/simulate", json={
        "user_context": {},
        "food_id": "00000000-0000-0000-0000-000000000000"
    })
    assert res.status_code == 401

def test_admin_simulator_denies_user(client):
    token = get_token(client, "user@nutriguard.com", "password123")
    res = client.post("/api/v1/admin/rules/simulate", 
        json={"user_context": {}, "food_id": "00000000-0000-0000-0000-000000000000"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403

def test_admin_simulator_allows_reviewer(client, db_session):
    from models.food import Food
    food = db_session.query(Food).first()
    
    token = get_token(client, "reviewer@nutriguard.com", "password123")
    res = client.post("/api/v1/admin/rules/simulate", 
        json={"user_context": {}, "food_id": str(food.food_id)},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    trace = res.json()
    assert "safety" in trace
    assert "allergy" in trace
    assert "interactions" in trace
    assert "scores" in trace
