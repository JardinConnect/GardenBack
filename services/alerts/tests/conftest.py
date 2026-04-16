import os

os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_key_32_bytes_minimum!!")
