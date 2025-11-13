from services.auth.utils.security import get_password_hash, verify_password 

def test_get_password_hash():
    password = "supersecret"
    hashed = get_password_hash(password)
    assert hashed != password 
    assert hashed.startswith("$2b$")

def test_verify_password_correct():
    password = "supersecret"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True 

def test_verify_password_incorrect():
    password = "supersecret"
    wrong_password = "wrongpassword"
    hashed = get_password_hash(password)
    assert verify_password(wrong_password, hashed) is False
