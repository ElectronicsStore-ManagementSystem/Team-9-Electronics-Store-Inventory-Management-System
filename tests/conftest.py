import os
os.environ["EIMS_DATABASE_URL"] = "sqlite:///./test_eims.db"
os.environ["EIMS_SECRET_KEY"] = "test-secret-key"
os.environ["EIMS_ENFORCE_HTTPS"] = "false"
import pytest
from fastapi.testclient import TestClient
from app.bootstrap import seed_demo_data
from app.db import Base, engine
from app.main import app
from app.db import SessionLocal
from sqlalchemy import delete
from app.models import (
    AuditLog,
    AvailabilityCheck,
    Branch,
    Component,
    DowntimeIncident,
    MaintenanceWindow,
    Supplier,
    User,
    StockMovement,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderReceipt,
)

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Delete dependent records first
    db.execute(delete(PurchaseOrderReceipt))
    db.execute(delete(PurchaseOrderItem))
    db.execute(delete(PurchaseOrder))

    db.execute(delete(StockMovement))
    db.execute(delete(AvailabilityCheck))
    db.execute(delete(DowntimeIncident))
    db.execute(delete(MaintenanceWindow))
    db.execute(delete(AuditLog))

# Delete parent records afterwards
    db.execute(delete(Supplier))
    db.execute(delete(Component))
    db.execute(delete(Branch))
    db.execute(delete(User))
    db.commit()
    db.close()

    seed_demo_data()
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
