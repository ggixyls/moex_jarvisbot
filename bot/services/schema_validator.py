import json
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator


class SchemaValidator:
    def __init__(self, schema_path: Path) -> None:
        with schema_path.open(encoding="utf-8") as schema_file:
            schema = json.load(schema_file)
        self._validator = Draft202012Validator(schema)

    def validate(self, data: dict) -> None:
        self._validator.validate(data)
