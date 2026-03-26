from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # GitHub
    github_app_id: str = ""
    github_private_key_path: str = ""
    github_webhook_secret: str = ""

    # LLM Provider: "openai" or "ollama"
    default_llm_provider: str = "ollama"

    # OpenAI API (works with any OpenAI-compatible endpoint)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    # Ollama (local LLM)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "codellama"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Database
    database_url: str = "sqlite:///./geekpr.db"

    # Defaults
    default_cc_threshold: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
