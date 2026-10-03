from app.security import hash_password, verify_password

def test_password_is_hashed_and_verifiable():
    encoded=hash_password('StrongPassword!')
    assert encoded != 'StrongPassword!'
    assert verify_password('StrongPassword!', encoded)
    assert not verify_password('wrong', encoded)

def test_salt_changes_hash():
    assert hash_password('same') != hash_password('same')
