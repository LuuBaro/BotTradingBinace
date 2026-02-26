import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.api.main import app

def test_login():
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    print("STATUS:", response.status_code)
    print("BODY:", response.text)

if __name__ == "__main__":
    test_login()
