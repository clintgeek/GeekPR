from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # GitHub
    github_app_id: str = ""
    github_private_key_path: str = ""
    github_webhook_secret: str = ""

    # LLM Provider: "aigeek" (default), "openai", or "ollama"
    # "aigeek" routes through baseGeek's OpenAI-compatible proxy, which
    # round-robins across free-tier providers and supports native structured
    # output on Anthropic/Gemini via provider/model pinning.
    default_llm_provider: str = "aigeek"

    # aiGeek (baseGeek's OpenAI-compatible endpoint)
    aigeek_base_url: str = "https://basegeek.clintgeek.com/openai/v1"
    aigeek_api_key: str = ""  # bg_<64-hex> — set in .env, never committed
    # "<provider>/<model>" pins a specific provider per request (see
    # baseGeek/DOCS/AIGEEK_USAGE.md). Anthropic gives the most consistent
    # structured output via native tool-use translation.
    aigeek_default_model: str = "anthropic/claude-sonnet-4-6"

    # OpenAI API direct (kept for testing against upstream OpenAI)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    # Ollama (local LLM — dev fallback)
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
