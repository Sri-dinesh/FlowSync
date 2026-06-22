from pathlib import Path
import base64
import json

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


SERVER_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = SERVER_ROOT / ".env"


class Settings(BaseSettings):
    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_service_key: str
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def cors_origins_list(self) -> list[str]:
        origins = []
        if self.cors_origins:
            origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]

        default_origins = [
            "https://flowsyncc.vercel.app",
            "https://flowsync.vercel.app",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ]
        for origin in default_origins:
            if origin not in origins:
                origins.append(origin)
        return origins

    @model_validator(mode="before")
    @classmethod
    def resolve_supabase_service_key(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        candidates = [
            data.get("SUPABASE_SECRET_KEY"),
            data.get("SUPABASE_SERVICE_ROLE_KEY"),
            data.get("SUPABASE_SERVICE_KEY"),
            data.get("SUPABASE_KEY"),
        ]

        for candidate in candidates:
            if isinstance(candidate, str) and cls._is_admin_supabase_key(candidate):
                data["supabase_service_key"] = candidate
                return data

        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                data["supabase_service_key"] = candidate
                return data

        return data

    @field_validator("supabase_service_key")
    @classmethod
    def validate_supabase_admin_key(cls, value: str) -> str:
        normalized = value.strip()

        if normalized.startswith("sb_publishable_"):
            raise ValueError("Supabase server writes require a secret/admin key, not a publishable key.")

        parts = normalized.split(".")
        if len(parts) >= 2:
            payload = parts[1] + "=" * (-len(parts[1]) % 4)
            try:
                decoded = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
            except Exception:
                raise ValueError("Supabase server writes require a secret/admin key, not an unrecognized JWT key.")

            if decoded.get("role") == "anon":
                raise ValueError("Supabase server writes require a service-role/admin key, not an anon key.")

        return normalized

    @staticmethod
    def _is_admin_supabase_key(value: str) -> bool:
        normalized = value.strip()
        if not normalized:
            return False
        if normalized.startswith("sb_secret_"):
            return True
        if normalized.startswith("sb_publishable_"):
            return False

        parts = normalized.split(".")
        if len(parts) < 2:
            return False

        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        try:
            decoded = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
        except Exception:
            return False

        return decoded.get("role") == "service_role"


settings = Settings()
