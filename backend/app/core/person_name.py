"""Normalization for new person-name inputs only; never apply to credentials."""
import unicodedata

MAX_RAW_NAME_LENGTH = 4096
MAX_NAME_LENGTH = 120
# These blank fillers have letter/symbol categories, unlike ordinary format
# controls and combining marks. Preserve them inside otherwise visible names.
_BLANK_FILLERS = frozenset("\u115f\u1160\u3164\uffa0\u2800")


def normalize_person_name(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Nome deve ser texto")
    if len(value) > MAX_RAW_NAME_LENGTH:
        raise ValueError("Entrada de nome excessivamente longa")
    if any(unicodedata.category(char) in {"Cc", "Cs"} for char in value):
        raise ValueError("Nome contém caracteres de controle ou Unicode inválido")
    # Reject controls first: a newline/tab must not be silently repaired.
    normalized = " ".join(unicodedata.normalize("NFC", value).split())
    if not normalized or not any(
        unicodedata.category(char)[0] in {"L", "N", "P", "S"}
        and char not in _BLANK_FILLERS for char in normalized
    ):
        raise ValueError("Nome deve conter conteúdo visível")
    if len(normalized) > MAX_NAME_LENGTH:
        raise ValueError("Nome deve ter no máximo 120 caracteres após normalização")
    return normalized
