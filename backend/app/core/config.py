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

    # Defaults — bumped from 10 because the reviewer is now severity-
    # filtered (CRITICAL/HIGH only), and 10 was catching every non-
    # trivial function for review. 15 still flags genuinely branchy
    # code; the LLM does final triage and drops style-only concerns.
    default_cc_threshold: int = 15

    # ─── Authentication (basegeek SSO) ──────────────────────────────────
    # Tri-state:
    #   "true"  — enforce basegeek session on every protected route
    #   "false" — no in-process auth; operator MUST protect the service
    #             upstream (nginx basic auth, VPN, mTLS, etc.)
    #   unset   — app refuses to start (see main.py startup guard). This
    #             is deliberate: no accidentally shipping a public API.
    basegeek_auth_enabled: str | None = None

    # basegeek's OpenAPI-compatible host. Used to verify sessions via
    # GET {basegeek_base_url}/api/users/me.
    basegeek_base_url: str = "https://basegeek.clintgeek.com"

    # Login page URL the frontend redirects unauthenticated users to.
    # basegeek appends ?token=... to the `redirect` param after login.
    basegeek_login_url: str = "https://basegeek.clintgeek.com/"

    # Cookie name basegeek sets for the access token. Domain is
    # .clintgeek.com, so every subdomain (including geekpr.clintgeek.com)
    # sees it automatically.
    basegeek_session_cookie: str = "geek_token"

    # How long (seconds) to cache a successful /api/users/me response
    # per-token. Token TTL is 1h upstream; a short in-process cache
    # keeps us from hitting basegeek on every single API call.
    basegeek_session_cache_ttl: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Tolerate extra .env keys that aren't declared on this Settings
        # class — lets a working-copy .env include variables for branches
        # that haven't merged yet (e.g. feature branches adding new config)
        # without breaking tests on branches that don't know about them.
        extra = "ignore"


settings = Settings()
