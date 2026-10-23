from app.security import hash_password, verify_password

def test_password_is_hashed_and_verifiable():
    encoded = hash_password("StrongPassword!")
    assert encoded != "StrongPassword!"
    assert encoded.startswith("pbkdf2_sha256$310000$")
    assert verify_password("StrongPassword!", encoded)
    assert not verify_password("wrong", encoded)

def test_salt_changes_hash():
    first = hash_password("same")
    second = hash_password("same")
    assert first != second
    assert first.split("$")[2] != second.split("$")[2]


def test_plaintext_password_is_never_accepted_as_a_stored_hash():
    assert not verify_password("StrongPassword!", "StrongPassword!")


def test_malformed_password_hashes_are_rejected():
    malformed_hashes = [
        "",
        "plaintext",
        "pbkdf2_sha256$invalid$00$00",
        "pbkdf2_sha256$999999999$00$00",
        "pbkdf2_sha256$310000$00$00",
        "unknown$310000$00$00",
    ]

    for encoded in malformed_hashes:
        assert not verify_password("StrongPassword!", encoded)

    assert not verify_password("StrongPassword!", None)
