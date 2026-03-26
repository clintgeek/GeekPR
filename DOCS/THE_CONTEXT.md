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

## Last Updated

- **2026-03-25**: Created as a living notebook for discoveries during implementation
- **2026-03-25**: Added dual LLM provider decision (OpenAI + Ollama), Docker networking note
