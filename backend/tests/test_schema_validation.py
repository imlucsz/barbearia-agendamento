import unittest

from pydantic import ValidationError

from support import main  # configures the isolated temporary SQLite test environment
from app.schemas.appointment import AdminAppointmentCreate, AvaliacaoCreate
from app.schemas.horario import BloqueioHorarioCreate
from app.schemas.institucional import InformacaoInstitucionalCreate
from app.schemas.service import ServiceCreate
from app.schemas.user import UserCreate


class SchemaValidationTests(unittest.TestCase):
    def test_user_name_and_email_limits_and_control_characters(self):
        with self.assertRaises(ValidationError):
            UserCreate.model_validate({
                "nome": "x" * 121, "email": "a@example.com", "senha": "strong-password",
                "consentimento_lgpd": True,
            })
        with self.assertRaises(ValidationError):
            UserCreate.model_validate({
                "nome": "Nome\u0000Invalido", "email": "a@example.com", "senha": "strong-password",
                "consentimento_lgpd": True,
            })
        with self.assertRaises(ValidationError):
            UserCreate.model_validate({
                "nome": "Nome", "email": "not-an-email", "senha": "strong-password",
                "consentimento_lgpd": True,
            })
        self.assertEqual(UserCreate.model_validate({
            "nome": "  Nome Seguro  ", "email": "a@example.com", "senha": "strong-password",
            "consentimento_lgpd": True,
        }).nome, "Nome Seguro")

    def test_service_description_price_duration_and_name_limits(self):
        base = {"nome": "Corte", "preco": 35.0, "duracao_minutos": 30}
        self.assertEqual(ServiceCreate.model_validate({**base, "descricao": "  Acabamento detalhado  "}).descricao, "Acabamento detalhado")
        for update in (
            {"preco": 0}, {"preco": 1000001}, {"duracao_minutos": 0},
            {"duracao_minutos": 1441}, {"duracao_minutos": "30"},
            {"nome": " "}, {"nome": "x" * 121}, {"descricao": "x" * 501},
        ):
            with self.subTest(update=update), self.assertRaises(ValidationError):
                ServiceCreate.model_validate({**base, **update})

    def test_institutional_phone_urls_lengths_and_control_characters(self):
        base = {
            "nome": "Barbearia", "endereco": "Rua de Teste, 1", "telefone": "11999990000",
            "email": "contato@example.com", "site": "https://example.com",
            "horario_funcionamento": "08:00-18:00", "dias_atendimento": "Todos os dias",
            "endereco_maps": "https://www.google.com/maps/embed?x=1",
        }
        invalid = (
            {"telefone": "telefone"}, {"site": "javascript:alert(1)"},
            {"endereco_maps": "https://maps.example.test/map"},
            {"nome": "x" * 121}, {"endereco": "x" * 301},
            {"horario_funcionamento": "x" * 201}, {"dias_atendimento": "x" * 121},
            {"endereco": "Rua\nInvalida"},
        )
        for update in invalid:
            with self.subTest(update=update), self.assertRaises(ValidationError):
                InformacaoInstitucionalCreate.model_validate({**base, **update})

    def test_review_note_comment_and_block_reason_limits(self):
        for note in (0, 6, "5"):
            with self.subTest(note=note), self.assertRaises(ValidationError):
                AvaliacaoCreate.model_validate({"nota": note, "comentario": "Comentário"})
        with self.assertRaises(ValidationError):
            AvaliacaoCreate.model_validate({"nota": 5, "comentario": "x" * 2001})
        with self.assertRaises(ValidationError):
            BloqueioHorarioCreate.model_validate({
                "barbeiro_id": 1, "inicio": "2027-01-01T08:00:00", "fim": "2027-01-01T09:00:00",
                "tipo": "folga", "motivo": "x" * 301,
            })

    def test_manual_customer_name_is_trimmed_and_bounded(self):
        base = {
            "service_id": 1, "barbeiro_id": 1, "data_hora": "2027-01-01T08:00:00",
            "nome_cliente": "  Cliente avulso  ",
        }
        self.assertEqual(AdminAppointmentCreate.model_validate(base).nome_cliente, "Cliente avulso")
        with self.assertRaises(ValidationError):
            AdminAppointmentCreate.model_validate({**base, "nome_cliente": "x" * 121})


if __name__ == "__main__":
    unittest.main()
