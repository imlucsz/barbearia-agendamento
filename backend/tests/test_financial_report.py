import csv
import io
import unittest
from datetime import datetime

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import create_access_token
from app.models.user import Appointment, AppointmentStatusEnum, RoleEnum, Service, User


class FinancialReportTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        db = main.SessionLocal()
        try:
            admin = self.add_user(db, "financial-admin@example.test", RoleEnum.ADMIN)
            self.add_user(db, "=CALL_ADMIN@example.test", RoleEnum.BARBEIRO, name="=CMD|' /C calc'!A0")
            self.add_user(db, "financial-barber@example.test", RoleEnum.BARBEIRO, name="Barbeiro B")
            service_a = Service(nome="@SUM(1+1)", preco=40, duracao_minutos=30)
            service_b = Service(nome="Corte B", preco=50, duracao_minutos=45)
            client = self.add_user(db, "financial-client@example.test", RoleEnum.CLIENTE)
            db.add_all([service_a, service_b])
            db.flush()
            self.emails = {"admin": admin.email, "barber": "=CALL_ADMIN@example.test"}
            barbers = db.query(User).filter(User.role == RoleEnum.BARBEIRO).order_by(User.id).all()
            self.create_appointment(db, client, barbers[0], service_a, datetime(2026, 6, 1, 10), AppointmentStatusEnum.CONCLUIDO, 32.5)
            self.create_appointment(db, client, barbers[0], service_a, datetime(2026, 6, 2, 10), AppointmentStatusEnum.AVALIADO, None)
            self.create_appointment(db, client, barbers[1], service_b, datetime(2026, 6, 2, 11), AppointmentStatusEnum.CONCLUIDO, 27.5)
            self.create_appointment(db, client, barbers[1], service_b, datetime(2026, 6, 2, 12), AppointmentStatusEnum.CANCELADO, None)
            self.create_appointment(db, client, barbers[1], service_b, datetime(2026, 6, 3, 12), AppointmentStatusEnum.FALTA, None)
            self.create_appointment(db, client, barbers[1], service_b, datetime(2026, 6, 4, 12), AppointmentStatusEnum.CONCLUIDO, 90)
            db.commit()
        finally:
            db.close()

    @staticmethod
    def add_user(db, email, role, name=None):
        user = User(nome=name or email, email=email, senha_hash="test-only", role=role)
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def create_appointment(db, client, barber, service, start, status, charge):
        db.add(Appointment(
            user_id=client.id, nome_cliente=client.nome, service_id=service.id,
            barbeiro_id=barber.id, data_hora=start, status=status, preco=service.preco,
            duracao_minutos=service.duracao_minutos, valor_cobrado=charge,
        ))

    def request(self, method, path, role="admin", return_headers=False):
        token = create_access_token({"sub": self.emails[role]})
        return asgi_request(
            self.app, method, path, headers={"Authorization": f"Bearer {token}"},
            return_headers=return_headers,
        )

    def test_report_has_inclusive_period_breakdowns_status_counts_and_existing_totals(self):
        status, body = self.request("GET", "/admin/relatorio?inicio=2026-06-01&fim=2026-06-03")
        self.assertEqual(status, 200, body)
        self.assertEqual(body["total_agendamentos"], 3)
        self.assertEqual(body["total_receita"], 100)
        self.assertAlmostEqual(body["ticket_medio"], 100 / 3)
        self.assertEqual(body["contagem_status"], {"concluido": 3, "cancelado": 1, "falta": 1})
        self.assertEqual(len(body["por_barbeiro"]), 2)
        self.assertEqual(len(body["por_servico"]), 2)
        self.assertEqual([row["dia"] for row in body["por_dia"]], ["2026-06-01", "2026-06-02"])
        self.assertEqual([row["receita"] for row in body["por_dia"]], [32.5, 67.5])

    def test_only_admin_can_access_report_and_invalid_period_is_rejected(self):
        status, _body = self.request("GET", "/admin/relatorio?inicio=2026-06-01&fim=2026-06-03", role="barber")
        self.assertEqual(status, 403)
        status, _body = self.request("GET", "/admin/relatorio?inicio=2026-06-03&fim=2026-06-01")
        self.assertEqual(status, 400)

    def test_csv_export_neutralizes_formula_prefixes(self):
        status, body, headers = self.request(
            "GET", "/admin/relatorio/csv?inicio=2026-06-01&fim=2026-06-03", return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertIn("text/csv", headers["content-type"])
        self.assertIn("attachment; filename=\"relatorio-financeiro-", headers["content-disposition"])
        rows = list(csv.reader(io.StringIO(body.lstrip("\ufeff"))))
        self.assertEqual(rows[0], ["data_hora", "barbeiro", "servico", "status", "valor_cobrado"])
        self.assertTrue(any(row[1].startswith("'=CMD") for row in rows[1:]))
        self.assertTrue(any(row[2] == "'@SUM(1+1)" for row in rows[1:]))

