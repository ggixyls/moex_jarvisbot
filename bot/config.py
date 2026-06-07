from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    whitelist_user_ids: list[int] = Field(default_factory=list, alias="WHITELIST_USER_IDS")
    kafka_bootstrap_servers: str = Field(alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_requests_topic: str = Field(default="tg.requests", alias="KAFKA_REQUESTS_TOPIC")
    kafka_responses_topic: str = Field(default="worker.responses", alias="KAFKA_RESPONSES_TOPIC")
    response_timeout_seconds: int = Field(default=60, alias="RESPONSE_TIMEOUT_SECONDS")
    rate_limit_per_minute: int = Field(default=10, alias="RATE_LIMIT_PER_MINUTE")
    max_input_length: int = Field(default=1000, alias="MAX_INPUT_LENGTH")
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("whitelist_user_ids", mode="before")
    @classmethod
    def parse_whitelist(cls, value: object) -> list[int]:
        if isinstance(value, list):
            return [int(item) for item in value]
        if isinstance(value, int):
            return [value]
        if isinstance(value, str):
            if not value.strip():
                return []
            return [int(item.strip()) for item in value.split(",") if item.strip()]
        return []


@lru_cache
def get_settings() -> Settings:
    return Settings()
