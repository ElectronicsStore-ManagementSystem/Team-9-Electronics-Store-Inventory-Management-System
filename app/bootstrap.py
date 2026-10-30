from sqlalchemy import inspect, text

from .db import Base, SessionLocal, engine
from .models import (
    AvailabilityCheck,
    Branch,
    Component,
    DowntimeIncident,
    MaintenanceWindow,
    User,
)
from .repositories import find_user_by_username, insert_seed_records
from .security import hash_password
def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        if not db.query(Branch).filter_by(
            normalized_name="main branch"
        ).first():
            db.add(Branch(name="Main Branch", normalized_name="main branch"))
            db.commit()

        if find_user_by_username(db, "admin"):
            return
        users = [
            User(
                username="admin",
                password_hash=hash_password("Admin@12345"),
                role="ADMIN",
            ),
            User(
                username="staff",
                password_hash=hash_password("Staff@12345"),
                role="STAFF",
            ),
        ]
        components = [
            Component(
                sku="EIMS-00001",
                name="Arduino Uno",
                category="Microcontroller",
                quantity=18,
                unit_price=650,
                supplier="TechSource",
                reorder_level=5,
            ),
            Component(
                sku="EIMS-00002",
                name="ESP32 Dev Board",
                category="Microcontroller",
                quantity=4,
                unit_price=520,
                supplier="TechSource",
                reorder_level=5,
            ),
            Component(
                sku="EIMS-00003",
                name="220 Ohm Resistor",
                category="Passive",
                quantity=0,
                unit_price=2.5,
                supplier="CircuitHub",
                reorder_level=20,
            ),
        ]
        insert_seed_records(db, users, components)
    finally:
        db.close()


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)

    component_columns = {
        column["name"]
        for column in inspect(engine).get_columns("components")
    }

    if "branch" not in component_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE components "
                    "ADD COLUMN branch VARCHAR(120) NOT NULL "
                    "DEFAULT 'Main Branch'"
                )
            )

    columns = {
        column["name"]
        for column in inspect(engine).get_columns("users")
    }

    if "last_activity" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN last_activity DATETIME")
            )

    db = SessionLocal()
    try:
        default_branch = db.query(Branch).filter_by(
            normalized_name="main branch"
        ).first()
        if default_branch is None:
            db.add(Branch(name="Main Branch", normalized_name="main branch"))
            db.commit()
    finally:
        db.close()

    seed_demo_data()