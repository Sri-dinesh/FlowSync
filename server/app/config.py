from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_service_key: str = Field(alias="SUPABASE_SERVICE_KEY")
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
