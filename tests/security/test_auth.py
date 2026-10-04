from backend.auth.service import hash_password, verify_password, has_role, session_expired
def test_password_is_hashed_and_verifiable():
    stored = hash_password("demo-password")
    assert stored != "demo-password"
    assert verify_password("demo-password", stored)
def test_rbac():
    assert has_role("Staff", {"Admin", "Manager", "Staff"})
    assert not has_role("Staff", {"Admin", "Manager"})
