from pydantic import BaseModel, EmailStr

class User(BaseModel):
    email: EmailStr

# Test OK
try:
    user = User(email="test@example.com")
    print("✅ Email valide :", user.email)
except Exception as e:
    print("❌ Erreur :", e)

# Test KO
try:
    user = User(email="pas_un_email")
    print("❌ Cela aurait dû échouer :", user.email)
except Exception as e:
    print("✅ Email invalide détecté :", e)
