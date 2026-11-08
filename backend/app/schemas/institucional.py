import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlsplit

from pydantic import EmailStr, Field, StrictStr, field_validator

from app.schemas.base import ORMModel, SchemaModel


_PHONE = re.compile(r"\+?[0-9][0-9 ()-]{5,18}[0-9]\Z")


def _validate_url(value: str | None, *, map_url: bool) -> str | None:
    if value is None:
        return None
    if not value:
        raise ValueError("Use null para remover uma URL opcional")
    if len(value) > 2048:
        raise ValueError("A URL deve ter no máximo 2048 caracteres")
    try:
        parsed = urlsplit(value)
        hostname = (parsed.hostname or "").lower()
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError
    except ValueError:
        raise ValueError("URL inválida") from None
    if parsed.scheme not in ({"https"} if map_url else {"http", "https"}) or not hostname:
        raise ValueError("URL deve usar um endereço HTTPS válido" if map_url else "URL deve usar HTTP ou HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URLs não podem incluir credenciais")
    if map_url and not any(
        hostname == domain or hostname.endswith("." + domain)
        for domain in ("google.com", "google.com.br")
    ):
        raise ValueError("O mapa deve usar um host Google Maps permitido")
    return value


class InformacaoInstitucionalBase(ORMModel):
    nome: StrictStr = Field(min_length=1, max_length=120)
    endereco: StrictStr = Field(min_length=1, max_length=300)
    telefone: StrictStr = Field(min_length=7, max_length=20)
    email: Optional[EmailStr] = Field(default=None, max_length=254)
    site: Optional[StrictStr] = Field(default=None, max_length=2048)
    horario_funcionamento: StrictStr = Field(min_length=1, max_length=200)
    dias_atendimento: StrictStr = Field(min_length=1, max_length=120)
    endereco_maps: Optional[StrictStr] = Field(default=None, max_length=2048)

    @field_validator("telefone")
    @classmethod
    def validate_phone(cls, value):
        if not _PHONE.fullmatch(value):
            raise ValueError("Telefone inválido")
        return value

    @field_validator("site")
    @classmethod
    def validate_site(cls, value):
        return _validate_url(value, map_url=False)

    @field_validator("endereco_maps")
    @classmethod
    def validate_map_url(cls, value):
        return _validate_url(value, map_url=True)


class InformacaoInstitucionalCreate(InformacaoInstitucionalBase):
    pass


class InformacaoInstitucionalUpdate(SchemaModel):
    nome: Optional[StrictStr] = Field(default=None, min_length=1, max_length=120)
    endereco: Optional[StrictStr] = Field(default=None, min_length=1, max_length=300)
    telefone: Optional[StrictStr] = Field(default=None, min_length=7, max_length=20)
    email: Optional[EmailStr] = Field(default=None, max_length=254)
    site: Optional[StrictStr] = Field(default=None, max_length=2048)
    horario_funcionamento: Optional[StrictStr] = Field(default=None, min_length=1, max_length=200)
    dias_atendimento: Optional[StrictStr] = Field(default=None, min_length=1, max_length=120)
    endereco_maps: Optional[StrictStr] = Field(default=None, max_length=2048)

    @field_validator("nome", "endereco", "telefone", "horario_funcionamento", "dias_atendimento", mode="before")
    @classmethod
    def reject_null_required_fields(cls, value):
        if value is None:
            raise ValueError("O campo não pode ser nulo")
        return value

    @field_validator("telefone")
    @classmethod
    def validate_phone(cls, value):
        if value is not None and not _PHONE.fullmatch(value):
            raise ValueError("Telefone inválido")
        return value

    @field_validator("site")
    @classmethod
    def validate_site(cls, value):
        return _validate_url(value, map_url=False)

    @field_validator("endereco_maps")
    @classmethod
    def validate_map_url(cls, value):
        return _validate_url(value, map_url=True)


class InformacaoInstitucionalResponse(InformacaoInstitucionalBase):
    id: int = Field(gt=0)
    criado_em: datetime
    atualizado_em: datetime
