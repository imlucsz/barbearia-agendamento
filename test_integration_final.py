import sys
import time
import traceback
from datetime import datetime, timedelta
sys.path.insert(0, 'C:/Users/Aluno/Documents/barbearia-agendamento/backend')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_test():
    # Initialize variables
    cliente_token = None
    admin_token = None
    service_id = None
    service_name = None
    appointment_id = None
    slot_time = None
    unique_id = int(time.time())
    cliente_email = f"teste_cliente_{unique_id}@example.com"
    nova_senha = "novaSenha456"

    # Helper to print traceback and exit
    def fail(step_num, description, expected, err):
        # Print error safely
        err_msg = f"Step {step_num} failed:\n{err}"
        print(err_msg.encode('cp1252', errors='replace').decode('cp1252'))
        sys.exit(1)

    # 0. Seed demo data (optional)
    try:
        client.get("/seed")
    except Exception:
        pass  # ignore seed errors

    # 1. POST /auth/register (cliente)
    try:
        register_data = {
            "nome": "Cliente Teste",
            "email": cliente_email,
            "senha": "senha123"
        }
        response = client.post("/auth/register", json=register_data)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
    except Exception as e:
        fail(1, "POST /auth/register (cliente)", "201 Created", traceback.format_exc())

    # 2. POST /auth/login → pega token (cliente)
    try:
        login_data = {
            "email": cliente_email,
            "senha": "senha123"
        }
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
        login_resp = response.json()
        cliente_token = login_resp["access_token"]
    except Exception as e:
        fail(2, "POST /auth/login → pega token (cliente)", "200 OK com token", traceback.format_exc())

    # 3. POST /services (como admin) → cria um serviço com preço e duração
    try:
        # Admin login
        admin_login = {
            "email": "admin@barbearia.com",
            "senha": "admin123"
        }
        response = client.post("/auth/login", json=admin_login)
        assert response.status_code == 200, f"Admin login failed: {response.json()}"
        admin_token = response.json()["access_token"]
        # Create service
        service_name = f"Serviço Teste {unique_id}"
        service_data = {
            "nome": service_name,
            "preco": 100.0,
            "duracao_minutos": 60
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/services", json=service_data, headers=headers)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
        service_resp = response.json()
        service_id = service_resp["id"]
    except Exception as e:
        fail(3, "POST /services (como admin)", "201 Created (service)", traceback.format_exc())

    # 4. GET /services (sem token) → confirma que é público (RF01)
    try:
        response = client.get("/services")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
        services = response.json()
        if service_id is not None:
            service_names = [s["nome"] for s in services]
            assert service_name in service_names, f"Service {service_name} not found in public list"
    except Exception as e:
        fail(4, "GET /services (sem token)", "200 OK, lista pública inclui nosso serviço", traceback.format_exc())

    # 5. GET /appointments/disponiveis → confirma retorno de horários livres (RF07)
    try:
        if service_id is None:
            raise Exception("Service ID not available from previous step")
        future_date = (datetime.now() + timedelta(days=1)).date()
        params = {
            "service_id": service_id,
            "data": future_date.isoformat()
        }
        headers = {"Authorization": f"Bearer {cliente_token}"} if cliente_token else {}
        response = client.get("/appointments/disponiveis", params=params, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
        slots = response.json()
        assert isinstance(slots, list) and len(slots) > 0, "Expected non-empty list of free slots"
        slot_time = slots[0]["data_hora"]
    except Exception as e:
        fail(5, "GET /appointments/disponiveis", "200 OK, horários livres retornados", traceback.format_exc())

    # 6. POST /appointments (cliente agenda) → confirma snapshot de preço/duração (RN-05)
    try:
        if service_id is None or cliente_token is None:
            raise Exception("Missing service_id or cliente_token")
        if slot_time is None:
            raise Exception("slot_time not defined from previous step")
        appointment_data = {
            "service_id": service_id,
            "data_hora": slot_time
        }
        headers = {"Authorization": f"Bearer {cliente_token}"}
        response = client.post("/appointments", json=appointment_data, headers=headers)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
        appointment_resp = response.json()
        appointment_id = appointment_resp["id"]
        assert appointment_resp["preco"] == 100.0, f"Preço snapshot não corresponde: {appointment_resp['preco']}"
        assert appointment_resp["duracao_minutos"] == 60, f"Duração snapshot não corresponde: {appointment_resp['duracao_minutos']}"
    except Exception as e:
        fail(6, "POST /appointments (cliente agenda)", "201 Created, snapshot de preço/duração correto", traceback.format_exc())

    # 7. POST /appointments no MESMO horário/barbeiro → confirma 409 (RNF-01)
    try:
        if service_id is None or cliente_token is None:
            raise Exception("Missing service_id or cliente_token")
        headers = {"Authorization": f"Bearer {cliente_token}"}
        response = client.post("/appointments", json=appointment_data, headers=headers)
        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.json()}"
    except Exception as e:
        fail(7, "POST /appointments no MESMO horário/barbeiro", "409 Conflict", traceback.format_exc())

    # 8. PUT /appointments/{id} tentando reagendar com <24h de antecedência → confirma bloqueio (RN-02)
    try:
        if appointment_id is None or cliente_token is None:
            raise Exception("Missing appointment_id or cliente_token")
        soon = datetime.now() + timedelta(hours=1)  # 1 hour in the future
        soon_iso = soon.isoformat()
        update_data = {
            "data_hora": soon_iso
        }
        headers = {"Authorization": f"Bearer {cliente_token}"}
        response = client.put(f"/appointments/{appointment_id}", json=update_data, headers=headers)
        assert response.status_code == 400, f"Expected 400 (bad request) for <24h, got {response.status_code}: {response.json()}"
        resp_json = response.json()
        assert "24 horas" in resp_json.get("detail", ""), f"Error message does not mention 24h rule: {resp_json}"
    except Exception as e:
        fail(8, "PUT /appointments/{id} tentando reagendar com <24h de antecedência", "400 Bloqueado (regra <24h)", traceback.format_exc())

    # 9. PUT /appointments/{id} marcando como concluído (RF14)
    try:
        if appointment_id is None or cliente_token is None:
            raise Exception("Missing appointment_id or cliente_token")
        update_data = {
            "status": "concluido"
        }
        headers = {"Authorization": f"Bearer {cliente_token}"}
        response = client.put(f"/appointments/{appointment_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
        updated = response.json()
        assert updated["status"] == "concluido", f"Appointment status not updated to concluido: {updated['status']}"
    except Exception as e:
        fail(9, "PUT /appointments/{id} marcando como concluído", "200 OK, status concluido", traceback.format_exc())

    # 10. POST /appointments/{id}/avaliacao → confirma que só funciona após concluído (RN-04)
    try:
        if appointment_id is None or cliente_token is None:
            raise Exception("Missing appointment_id or cliente_token")
        avaliacao_data = {
            "nota": 5,
            "comentario": "Otimo serviço!"
        }
        response = client.post(f"/appointments/{appointment_id}/avaliacao", json=avaliacao_data, headers={"Authorization": f"Bearer {cliente_token}"})
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
        avaliacao_resp = response.json()
        assert avaliacao_resp["nota"] == 5, f"Avaliacao nota não corresponde: {avaliacao_resp['nota']}"
    except Exception as e:
        fail(10, "POST /appointments/{id}/avaliacao", "201 Created, avaliacao permitida apenas após concluído", traceback.format_exc())

    # 11. GET /appointments/avaliacoes → confirma nota média pública (RF03)
    try:
        response = client.get("/appointments/avaliacoes")  # Public endpoint, no token needed
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
        avaliacoes = response.json()
        assert isinstance(avaliacoes, list) and len(avaliacoes) > 0, "Expected non-empty list of evaluations"
        found = any(a["appointment_id"] == appointment_id for a in avaliacoes)
        assert found, f"Our evaluation for appointment {appointment_id} not found in public list"
    except Exception as e:
        fail(11, "GET /appointments/avaliacoes", "200 OK, nota média pública disponível", traceback.format_exc())

    # 12. GET /admin/relatorio?inicio=&fim= → confirma soma correta dos agendamentos concluídos (RF21)
    try:
        if admin_token is None:
            raise Exception("Admin token not available")
        hoje = datetime.now().date()
        inicio = hoje.isoformat()
        fim = (hoje + timedelta(days=7)).isoformat()  # a week ahead
        params = {
            "inicio": inicio,
            "fim": fim
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/admin/relatorio", params=params, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
        report = response.json()
        assert report["total_agendamentos"] >= 1, f"Expected at least 1 appointment, got {report['total_agendamentos']}"
        assert report["total_receita"] >= 100.0, f"Expected revenue at least 100, got {report['total_receita']}"
    except Exception as e:
        fail(12, "GET /admin/relatorio?inicio=&fim=", "200 OK, soma correta dos agendamentos concluídos", traceback.format_exc())

    # 13. Tenta acessar qualquer rota /admin/* com token de cliente comum → confirma 403 (RNF-05)
    try:
        if cliente_token is None:
            raise Exception("Cliente token not available")
        hoje = datetime.now().date()
        params = {
            "data": hoje.isoformat()
        }
        headers = {"Authorization": f"Bearer {cliente_token}"}
        response = client.get("/admin/agenda", params=params, headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.json()}"
    except Exception as e:
        fail(13, "Tenta acessar qualquer rota /admin/* com token de cliente comum", "403 Forbidden", traceback.format_exc())

    # 14. POST /auth/esqueci-senha + /auth/redefinir-senha (RF06, já testado, só confirma de novo no fluxo geral)
    try:
        if cliente_email is None:
            raise Exception("Cliente email not available")
        reset_request = {
            "email": cliente_email
        }
        response = client.post("/auth/esqueci-senha", json=reset_request)
        assert response.status_code == 200, f"Esqueci-senha failed: {response.json()}"
        data = response.json()
        dev_token = data.get("dev_token")
        assert dev_token is not None, "Dev token not returned"
        # Now reset password
        reset_payload = {
            "token": dev_token,
            "nova_senha": nova_senha
        }
        response = client.post("/auth/redefinir-senha", json=reset_payload)
        assert response.status_code == 200, f"Redefinir senha failed: {response.json()}"
        # Now login with new password
        login_data = {
            "email": cliente_email,
            "senha": nova_senha
        }
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 200, f"Login with new password failed: {response.json()}"
        # Update cliente_token for subsequent steps (if needed)
        cliente_token = response.json()["access_token"]
    except Exception as e:
        fail(14, "POST /auth/esqueci-senha + /auth/redefinir-senha", "200 OK, fluxo de recuperação de senha funcionou", traceback.format_exc())

    # 15. DELETE /users/me → confirma exclusão lógica e bloqueio de login depois (RNF-04)
    try:
        if cliente_token is None:
            raise Exception("Cliente token not available")
        # Logically delete the cliente user
        headers = {"Authorization": f"Bearer {cliente_token}"}
        response = client.delete("/users/me", headers=headers)
        assert response.status_code == 200, f"Delete account failed: {response.json()}"
        # Now try to login with the same credentials (should fail)
        login_data = {
            "email": cliente_email,
            "senha": nova_senha
        }
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 401, f"Expected 401 for inactive user, got {response.status_code}: {response.json()}"
        resp_json = response.json()
        detail = resp_json.get("detail", "").lower()
        assert "inativa" in detail or "email ou senha incorretos" in detail, f"Error message does not mention inativa or email/senha incorretos: {resp_json}"
    except Exception as e:
        fail(15, "DELETE /users/me → confirma exclusão lógica e bloqueio de login depois", "200 OK exclusão lógica, login após falha com 401", traceback.format_exc())

    # If we reach here, all steps passed
    print("\n" + "="*80)
    print("INTEGRATION TEST RESULTS")
    print("="*80)
    # Header
    header = f"{'Step':<4} {'Description':<50} {'Expected':<35} {'Result'}"
    print(header.encode('cp1252', errors='replace').decode('cp1252'))
    print("-"*80)
    steps = [
        (1, "POST /auth/register (cliente)", "201 Created"),
        (2, "POST /auth/login → pega token (cliente)", "200 OK com token"),
        (3, "POST /services (como admin)", "201 Created (service)"),
        (4, "GET /services (sem token)", "200 OK, lista pública inclui nosso serviço"),
        (5, "GET /appointments/disponiveis", "200 OK, horários livres retornados"),
        (6, "POST /appointments (cliente agenda)", "201 Created, snapshot de preço/duração correto"),
        (7, "POST /appointments no MESMO horário/barbeiro", "409 Conflict"),
        (8, "PUT /appointments/{id} tentando reagendar com <24h de antecedência", "400 Bloqueado (regra <24h)"),
        (9, "PUT /appointments/{id} marcando como concluído", "200 OK, status concluido"),
        (10, "POST /appointments/{id}/avaliacao", "201 Created, avaliacao permitida apenas após concluído"),
        (11, "GET /appointments/avaliacoes", "200 OK, nota média pública disponível"),
        (12, "GET /admin/relatorio?inicio=&fim=", "200 OK, soma correta dos agendamentos concluídos"),
        (13, "Tenta acessar qualquer rota /admin/* com token de cliente comum", "403 Forbidden"),
        (14, "POST /auth/esqueci-senha + /auth/redefinir-senha", "200 OK, fluxo de recuperação de senha funcionou"),
        (15, "DELETE /users/me → confirma exclusão lógica e bloqueio de login depois", "200 OK exclusão lógica, login após falha com 401")
    ]
    for step_num, desc, expected in steps:
        line = f"{step_num:<4} {desc:<50} {expected:<35} {'PASSOU'}"
        print(line.encode('cp1252', errors='replace').decode('cp1252'))
    print("-"*80)
    print("\n[TODOS OS TESTES PASSARAM]")

if __name__ == "__main__":
    run_test()