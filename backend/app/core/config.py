import logging
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    app_name: str = "ALIGN API"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://align_user:align_dev_password@localhost:5433/align_db"
    jwt_secret_key: str = "CHANGE_ME_TO_A_LONG_RANDOM_SECRET_BEFORE_DEPLOYMENT"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str, info) -> str:
        # In production environments, weak or placeholder JWT keys are strictly forbidden
        if v == "CHANGE_ME_TO_A_LONG_RANDOM_SECRET_BEFORE_DEPLOYMENT":
            logger.warning(
                "SECURITY WARNING: ALIGN is using default JWT_SECRET_KEY placeholder. "
                "Ensure a high-entropy secret is configured before production deployment."
            )
        return v
    
    # Google OAuth
    google_client_id: str | None = None
    google_client_secret: str | None = None
    
    # SMTP Email Settings
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "noreply@align.local"
    smtp_use_tls: bool = True

    # Eventbrite API
    eventbrite_api_key: str | None = None
    eventbrite_api_secret: str | None = None
    eventbrite_private_token: str | None = None
    eventbrite_public_token: str | None = None

    # External APIs (GitHub, Kaggle, Nominatim OpenStreetMap)
    github_token: str | None = None
    kaggle_username: str | None = None
    kaggle_key: str | None = None
    nominatim_user_agent: str = "ALIGN-Platform/1.0 (+https://align.local)"

    # ML Recommendation Engine
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384

    # Neo4j Graph Database
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "align_dev_password"

    # AI Assistant V2 Configurations
    assistant_v2_enabled: bool = True
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str | None = None
    tavily_api_key: str | None = None
    serpapi_api_key: str | None = None

    # Instagram API with Instagram Login (Meta)
    instagram_app_id: str | None = None
    instagram_app_secret: str | None = None
    instagram_redirect_uri: str = "http://localhost:8000/api/v1/instagram/callback"
    instagram_enabled: bool = False
    token_encryption_key: str | None = None

    # Logging and Observability
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        raw = [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]
        # Disallow wildcard '*' when allow_credentials=True for OWASP CORS compliance
        safe = [o for o in raw if o != "*"]
        if safe:
            return safe
        if self.environment.lower() == "production":
            logger.warning("[CORS WARNING] No production CORS origins defined. Only same-origin allowed.")
            return []
        return ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://localhost:8000"]

settings = Settings()
