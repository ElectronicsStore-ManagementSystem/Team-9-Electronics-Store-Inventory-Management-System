import os
os.environ["EIMS_DATABASE_URL"] = "sqlite:///./test_eims.db"
os.environ["EIMS_SECRET_KEY"] = "test-secret-key"
import pytest
from fastapi.testclient import TestClient
from app.db import Base, engine
from app.main import app, seed
from app.db import SessionLocal
from sqlalchemy import delete
from app.models import AuditLog, Component, User

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    db.execute(delete(AuditLog)); db.execute(delete(Component)); db.execute(delete(User)); db.commit(); db.close()
    seed()
    yield

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def admin_token(client):
    return client.post('/api/auth/login',json={'username':'admin','password':'Admin@12345'}).json()['access_token']

@pytest.fixture
def staff_token(client):
    return client.post('/api/auth/login',json={'username':'staff','password':'Staff@12345'}).json()['access_token']
