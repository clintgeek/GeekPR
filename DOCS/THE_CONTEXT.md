# geekPR — Living Context

A notebook for discoveries, decisions, and critical success factors we learn *as we build*. This is not a duplicate of THE_PLAN or THE_STEPS — it's for things we discover during implementation that don't fit elsewhere.

---

## Critical Success Factors

These are non-negotiable for the project to work:

1. **Webhook signature verification must happen first** — Never process a webhook without validating the `X-Hub-Signature-256` header. Use `hmac.compare_digest()` for timing-safe comparison.

2. **Async processing is mandatory** — GitHub webhooks timeout at 10 seconds. If we analyze synchronously on large PRs, GitHub will retry and we'll post duplicate reviews. Celery + Redis is the only safe approach.

3. **LLM output validation is critical** — Both OpenAI and Ollama can hallucinate. Instructor's schema validation prevents the app from crashing on bad JSON. Without it, one bad LLM response breaks the entire pipeline.

4. **Database migrations must run before the app starts** — In Docker, the backend container will fail if the database schema doesn't exist. The entrypoint must run `alembic upgrade head` before starting Uvicorn.

5. **The GitHub App private key must never be committed** — Store it in `.env` (gitignored) and load via `GITHUB_PRIVATE_KEY_PATH`. One leaked key compromises the entire installation.

---

## Discoveries & Gotchas

Record things we find out the hard way here.

### [Phase X] — [Title]

**What we discovered**: 
- 

**Why it matters**: 
- 

**How to avoid it**: 
- 

---

## Implementation Decisions Made

When we choose a specific approach during coding, document it here with the rationale.

### Dual LLM Provider Support (OpenAI + Ollama)

**What we decided**: 
- Support both OpenAI API and Ollama as LLM providers, switchable per-repo via the dashboard Settings page.
- Global default set via `DEFAULT_LLM_PROVIDER` env var (defaults to `ollama`).
- OpenAI settings: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` in `.env`.
- `openai_base_url` is configurable so users can point at Azure OpenAI, Together AI, or any OpenAI-compatible endpoint.
- Each repo's `RepoConfig` has a `llm_provider` column (`"openai"` or `"ollama"`) and `llm_model` column.
- `get_llm_client()` in `llm.py` resolves the correct `OpenAI` client based on provider.

**Why**: 
- Not everyone wants to run Ollama locally (slow on CPU, needs GPU).
- OpenAI API gives faster, higher-quality results for production use.
- Making the base URL configurable means this also works with self-hosted or third-party OpenAI-compatible APIs.

**Alternatives we rejected**: 
- Hardcoding provider choice globally (no per-repo flexibility).
- Adding a separate LiteLLM proxy layer (unnecessary complexity — the `openai` SDK already handles both).

### Docker Networking for Ollama

**What we decided**:
- In `docker-compose.yml`, override `OLLAMA_BASE_URL` to `http://host.docker.internal:11434` so containers can reach Ollama running on the host machine.
- Uses `${OLLAMA_BASE_URL:-http://host.docker.internal:11434}` syntax so it's overridable.

**Why**:
- `localhost` inside a container refers to the container itself, not the host. `host.docker.internal` is Docker's built-in DNS for reaching the host.

---

## Performance Notes

Track performance bottlenecks and optimizations as we discover them.

- **LLM inference time**: Ollama on CPU is slow. OpenAI API is faster but costs money. Measure actual latency once we have a working pipeline. Per-repo provider choice lets teams optimize cost vs speed.
- **Diff parsing**: Large PRs with many files could be slow. Profile `extract_changed_functions()` on real diffs.
- **Database queries**: Monitor query performance in the dashboard. Add indexes if needed.

---

## Known Issues & Workarounds

Issues we've hit and how we worked around them.

- (None yet — will populate as we build)

---

## Testing Insights

Things we learn about testing this specific project.

- (None yet — will populate as we test)

---

## Deployment Lessons

Things we learn when deploying to production.

- (None yet — will populate as we deploy)

---

## Team Notes

Quick reminders for anyone working on this.

- Always check THE_PLAN.md for architecture and requirements.
- Always check THE_STEPS.md for implementation instructions.
- Use this file (THE_CONTEXT.md) for discoveries and gotchas.
- Update this file as you learn things — don't wait until the end.

---

## Implementation Decision — Language-Dispatched Analyzer Registry (2026-04-21)

**What we decided:**
- Extracted the Python-specific analyzer logic (function extraction, cyclomatic complexity via Radon, security via Bandit) behind an `Analyzer` protocol in `app/services/analyzers/`. Added JavaScript/TypeScript, Rust, and Go analyzers implementing the same protocol. Dispatch by file extension in `registry.py`; the pipeline in `analyze_pr.py` stays language-agnostic.

**Why it matters:**
- Made geekPR useful for more than just Python codebases (the original regex-based function extraction and Radon are Python-only). Also decoupled the pipeline from tool choice — swapping, say, ESLint for Biome in the JS analyzer is now a one-file change.

**Design constraints:**
- All non-Python analyzers shell out to external tools (eslint, cargo clippy, gocyclo, gosec). Every subprocess invocation fails-open — missing binary, timeout, or unparseable output returns `[]` rather than raising. This keeps the pipeline robust when a PR includes a language whose tool isn't installed on the analysis host.
- Rust has no standard CC tool, so `RustAnalyzer.analyze_complexity` is a heuristic (counts `if`/`else if`/`while`/`for`/`loop`/`&&`/`||` plus `match` arms). Labeled as approximate in the module docstring.

**How to add another language:** Drop a module in `analyzers/`, implement `extract_changed_functions` + `analyze_complexity` + `run_security_scan`, append an instance to `_ANALYZERS` in `registry.py`. No pipeline changes.

---

## Implementation Decision — LLM Default Switched to aiGeek (2026-04-21)

**What we decided:**
- Default LLM target is aiGeek (baseGeek's OpenAI-compatible proxy at `/openai/v1/chat/completions`). Direct OpenAI and Ollama paths remain for testing and local dev.
- Default `llm_model` is `anthropic/claude-3-5-sonnet-20241022` — aiGeek's explicit provider-pinning syntax bypasses rotation, so each PR review runs on a single deterministic backend.

**Why it matters:**
- `instructor` (our Pydantic-validated response layer) needs `response_format: {type: "json_schema"}` to work reliably. aiGeek maps that to native tool-use forced-choice on Anthropic + `responseSchema` on Gemini, which means the round-trip works end-to-end without us writing any prompt-engineering workarounds. Non-Anthropic/Gemini providers fall back to aiGeek's prompt-injection + JSON-repair path.
- aiGeek's rotation gives us "coding for free" on low-priority PR reviews without touching billable providers.

**How to configure:** `AIGEEK_BASE_URL`, `AIGEEK_API_KEY` (`bg_<64-hex>` with `ai:call` permission), `AIGEEK_DEFAULT_MODEL` in `.env`. See `.env.example`.

---

## Implementation Decision — basegeek SSO Integration (2026-04-21)

**What we decided:**
- geekPR integrates with baseGeek's SSO rather than building its own auth. Tri-state config (`BASEGEEK_AUTH_ENABLED=true|false|<unset>`); app refuses to start if unset so no one accidentally ships a public API. `true` enforces; `false` explicitly runs with no in-process auth and a loud warning (operator must protect upstream).
- Backend: FastAPI dependency (`app/core/auth.require_basegeek_user`) reads the `geek_token` cookie, validates against `GET https://basegeek.clintgeek.com/api/users/me`, caches the successful `/me` response in-process for 60s per token. Applied as a router-level dependency so adding a new route is protected by default.
- Frontend: Next.js middleware (`src/middleware.ts`) at the edge — checks the cookie, 302 to basegeek login if missing, before any page shell renders. No pre-auth flicker.
- Webhook (`POST /api/webhook/github`) stays unauthenticated — its HMAC signature check is its auth, GitHub can't carry a basegeek cookie.

**Why it matters:**
- Dashboards, reviews, and jobs were all publicly visible before this. Drive-by attackers could read review contents across all repos and modify per-repo config via PUT.
- Dogfoods the GeekSuite SSO platform — same login flow as notegeek/fitnessgeek/bujogeek. User lands at geekpr.clintgeek.com, gets bounced to basegeek, lands back at the dashboard signed in.

**Design constraints:**
- basegeek sets cookie `Domain=.clintgeek.com`, so every suite subdomain sees the session automatically. No separate login per app.
- Cookie is `HttpOnly`, so JS can't read it — frontend calls `/api/auth/me` to get identity.
- Refresh-token rotation is enforced upstream; geekPR doesn't manage refreshes (if the token expires mid-session, the /me call 401s and the frontend bounces back to login).
- httpx timeout on the /me verify call is 5s; longer = DoS vector.

**What to change if we ever want to support non-basegeek auth (e.g. Auth0):**
- `app/core/auth.py` is the seam. Replace `_verify_with_basegeek` with an OIDC-capable verifier. Keep the dependency signature and cache intact — route modules won't need to change.

---

## Last Updated

- **2026-03-25**: Created as a living notebook for discoveries during implementation
- **2026-03-25**: Added dual LLM provider decision (OpenAI + Ollama), Docker networking note
- **2026-04-21**: Multi-language analyzer registry (JS/TS, Rust, Go); LLM default → aiGeek
- **2026-04-21**: basegeek SSO integration with tri-state opt-out; webhook stays HMAC-only
