import unittest
from pydantic import ValidationError
from app.schemas.service import ServiceCreate, ServiceUpdate
from app.schemas.appointment import AvaliacaoCreate
from app.schemas.institucional import InformacaoInstitucionalUpdate


class BookingInputSafetyTests(unittest.TestCase):
    def test_service_create_and_update_preserve_literal_text_and_same_limits(self):
        payload = '<img src=x onerror="alert(1)"> & João'
        created = ServiceCreate(nome=payload, descricao=payload, preco=25, duracao_minutos=60)
        updated = ServiceUpdate(nome=payload, descricao=payload)
        self.assertEqual(created.nome, updated.nome)
        self.assertEqual(created.descricao, payload)
        for model in (ServiceCreate, ServiceUpdate):
            for values in ({"nome": "a" * 121}, {"descricao": "a" * 501},
                           {"duracao_minutos": 1441}, {"preco": float("inf")}):
                with self.assertRaises(ValidationError):
                    model(**({"nome": "Corte", "preco": 25, "duracao_minutos": 60} | values))

    def test_comments_are_bounded_plain_text_and_not_html_sanitized(self):
        payload = '<svg onload="alert(1)">'
        self.assertEqual(AvaliacaoCreate(nota=5, comentario=payload).comentario, payload)
        with self.assertRaises(ValidationError):
            AvaliacaoCreate(nota=5, comentario="a" * 2001)
        with self.assertRaises(ValidationError):
            AvaliacaoCreate(nota="5")

    def test_institutional_urls_reject_script_schemes_and_preserve_legitimate_text(self):
        self.assertEqual(InformacaoInstitucionalUpdate(nome="Barba & Cabelo <Centro>").nome, "Barba & Cabelo <Centro>")
        for field in ("site", "endereco_maps"):
            for url in ("javascript:alert(1)", "data:text/html,<script>alert(1)</script>", "https://user:pass@example.com"):
                with self.assertRaises(ValidationError):
                    InformacaoInstitucionalUpdate(**{field: url})
