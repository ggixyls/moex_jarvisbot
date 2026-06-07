from datetime import datetime, timezone
from uuid import uuid4

import pytest

from bot.config import PROJECT_ROOT
from bot.services.schema_validator import SchemaValidator


def test_tg_request_schema_valid() -> None:
    validator = SchemaValidator(PROJECT_ROOT / "schemas" / "tg.requests.schema.json")
    payload = {
        "request_id": str(uuid4()),
        "user_id": 1,
        "username": "tester",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intent": "diagnose_auth",
        "payload": {"username": "ivanov", "domain": "corp.local"},
    }
    validator.validate(payload)


def test_tg_request_schema_invalid_intent() -> None:
    validator = SchemaValidator(PROJECT_ROOT / "schemas" / "tg.requests.schema.json")
    payload = {
        "request_id": str(uuid4()),
        "user_id": 1,
        "username": "tester",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intent": "unknown",
        "payload": {},
    }
    with pytest.raises(Exception):
        validator.validate(payload)
