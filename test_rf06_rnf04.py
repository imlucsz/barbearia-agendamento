import sys
import time
sys.path.insert(0, 'C:/Users/Aluno/Documents/barbearia-agendamento/backend')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_rf06_rnf04():
    # Generate a unique email to avoid conflicts
    unique_id = int(time.time())
    email = f"teste_{unique_id}@example.com"

    # 1. Register a new user
    register_data = {
        "nome": "Teste User",
        "email": email,
        "senha": "senha123"
    }
    response = client.post("/auth/register", json=register_data)
    assert response.status_code == 201, f"Register failed: {response.json()}"
    print("[OK] Register successful")

    # 2. Request password reset (esqueci-senha)
    reset_request = {
        "email": email
    }
    response = client.post("/auth/esqueci-senha", json=reset_request)
    assert response.status_code == 200, f"Esqueci senha failed: {response.json()}"
    data = response.json()
    # In dev, we get a dev_token
    dev_token = data.get("dev_token")
    assert dev_token is not None, "Dev token not returned in response"
    print("[OK] Esqueci-senha successful, dev_token received")

    # 3. Redefine password with the token
    new_password = "novaSenha456"
    reset_payload = {
        "token": dev_token,
        "nova_senha": new_password
    }
    response = client.post("/auth/redefinir-senha", json=reset_payload)
    assert response.status_code == 200, f"Redefinir senha failed: {response.json()}"
    print("[OK] Redefinir senha successful")

    # 4. Login with the new password
    login_data = {
        "email": email,
        "senha": new_password
    }
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200, f"Login failed: {response.json()}"
    login_data = response.json()
    assert "access_token" in login_data, "Access token not in login response"
    print("[OK] Login com a nova senha successful")

    # Optional: Test logical deletion (RNF-04)
    # We need to be logged in to delete the account
    access_token = login_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.delete("/users/me", headers=headers)
    assert response.status_code == 200, f"Delete account failed: {response.json()}"
    print("[OK] Logical deletion (RNF-04) successful")

    # Verify that the user is now inactive (cannot login)
    login_again = {
        "email": email,
        "senha": new_password
    }
    response = client.post("/auth/login", json=login_again)
    assert response.status_code == 401, f"Login should fail for inactive user: {response.json()}"
    print("[OK] Inactive user cannot login")

    print("\n[OK] All tests passed!")

if __name__ == "__main__":
    try:
        test_rf06_rnf04()
    except Exception as e:
        print(f"\n[FAIL] Teste falhou: {e}")
        sys.exit(1)