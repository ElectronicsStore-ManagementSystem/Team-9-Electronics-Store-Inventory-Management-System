from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine
from .models import (
    AvailabilityCheck,
    Branch,
    Component,
    DowntimeIncident,
    MaintenanceWindow,
    Supplier,
    UserActionLog,
    User,
)
from .config import SUPER_ADMIN_PASSWORD, SUPER_ADMIN_USERNAME
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

        if find_user_by_username(db, SUPER_ADMIN_USERNAME) is None:
            db.add(
                User(
                    username=SUPER_ADMIN_USERNAME,
                    password_hash=hash_password(SUPER_ADMIN_PASSWORD),
                    role="SUPER_ADMIN",
                )
            )
            db.commit()

        if find_user_by_username(db, "admin"):
            _sync_component_suppliers(db)
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
        _sync_component_suppliers(db)
    finally:
        db.close()


def _sync_component_suppliers(db: Session) -> None:
    existing_names = {
        name.casefold()
        for name in db.scalars(select(Supplier.normalized_name))
    }

    for name in db.scalars(select(Component.supplier).distinct()):
        normalized_name = name.strip().casefold()
        display_name = name.strip()
        if display_name and normalized_name not in existing_names:
            db.add(
                Supplier(
                    name=display_name,
                    normalized_name=normalized_name,
                )
            )
            existing_names.add(normalized_name)

    db.commit()


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