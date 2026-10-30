import unicodedata

from pydantic import BaseModel, ConfigDict, model_validator


class SchemaModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def reject_control_characters(cls, value):
        def walk(item):
            if isinstance(item, str):
                return any(unicodedata.category(character) == "Cc" for character in item)
            if isinstance(item, dict):
                return any(walk(key) or walk(child) for key, child in item.items())
            if isinstance(item, (list, tuple)):
                return any(walk(child) for child in item)
            return False

        if walk(value):
            raise ValueError("Campos não podem conter caracteres de controle")
        return value


class ORMModel(SchemaModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
