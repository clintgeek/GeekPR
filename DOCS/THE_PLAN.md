# Project Spec: geekPR (The Autonomous Reviewer)







































































































































































































































































































































## 1. Objective

A self-hosted GitHub App that intercepts Pull Requests, performs static complexity analysis, and uses a local LLM to suggest refactors for "smelly" code directly in the PR comments.

## 2. Core Functional Requirements

- **Webhook Listener**: A FastAPI server that listens for GitHub pull_request events.
- **Diff Analyzer**: Uses PatchSet to isolate only the changed lines (don't waste tokens on the whole repo).
- **Complexity Guard**: Runs Radon to calculate Cyclomatic Complexity. If CC > 10, it flags the function.
- **Agentic Refactor**: Passes the high-complexity code to an LLM (OpenAI API or local Ollama) to generate a "clean code" alternative. Provider is switchable per-repo.
- **GitHub Integration**: Posts the suggestion as a formatted Markdown comment on the specific line of code.

## 3. Technical Stack

### Backend

| Component | Technology |
|-----------|------------|
| Server | FastAPI + Uvicorn |
| GitHub API | PyGithub |
| Code Metrics | Radon (Complexity) + Bandit (Security) |
| AI Orchestration | Instructor (for structured tool-calling) |
| LLM Providers | OpenAI API (configurable key + URL) **or** Ollama (local, codellama/deepseek-coder). Switchable per-repo via dashboard. |
| Task Queue | Celery + Redis (async PR processing) |
| Database | SQLite (dev) / PostgreSQL (prod) via SQLAlchemy |
| Config | python-dotenv + Pydantic Settings |

### Frontend (Dashboard)

| Component | Technology |
|-----------|------------|
| Framework | Next.js (React) |
| Styling | TailwindCSS v4 |
| Components | shadcn/ui |
| Icons | Lucide |
| Charts | Recharts |
| Data Fetching | TanStack Query |
| Theme | Dark-mode-first, terminal/hacker aesthetic |

## 4. Logic Flow

1. **Event**: Developer pushes to feature-branch.
2. **Trigger**: GitHub sends a signed JSON payload to the geekPR webhook endpoint.
3. **Verification**: Validate the webhook signature (HMAC-SHA256) before processing.
4. **Enqueue**: Push the job to the task queue (Celery/Redis) and return `202 Accepted` immediately — avoids webhook timeout on large diffs.
5. **Extraction**: Worker clones the diff and identifies new/modified functions.
6. **Static Scan**:
   - Radon checks for "God Functions" (CC threshold is configurable per-repo).
   - Bandit checks for hardcoded "secrets" or eval() calls.
7. **LLM Prompting**: Route to the configured provider (OpenAI API or Ollama). Prompt: "Act as a Staff Engineer. This function has a complexity score of {score}. Refactor it to be more modular. Use Type Hints and Docstrings."
8. **Structured Parsing**: Validate LLM output against a Pydantic schema before posting.
9. **Reporting**: Call the GitHub API to leave a review comment on the specific line.
10. **Logging**: Persist the review to the database for dashboard display and analytics.

## 5. The "Senior" Edge

To move this from "cool script" to "enterprise tool":

- **Secret Management**: Use python-dotenv and explain in the README why you aren't hardcoding GitHub PATs (Personal Access Tokens).
- **Structured Output**: Use Pydantic with Instructor to force the LLM to return JSON (e.g., `{ "line": 42, "suggestion": "...", "priority": "High" }`) so the app doesn't crash on "hallucinations."
- **Rate Limiting**: Implement basic logic to ensure you don't spam the GitHub API and get your IP flagged.

## 6. Dashboard UI

The dashboard is the user-facing brain of geekPR — where teams monitor, configure, and explore reviews.

### Pages & Views

- **PR Review Feed** (Home): A real-time stream of analyzed PRs. Each card shows repo name, PR title, number of flagged functions, top complexity score, and status (pending / reviewed / error). Filterable by repo, date, and severity.
- **Review Detail**: Drill into a single PR. Side-by-side view of the original code and LLM-suggested refactor, with per-function complexity badges and accept/dismiss actions.
- **Analytics**: Line charts for average complexity over time, bar charts for most-flagged files/contributors, and a heatmap of review activity by day/hour.
- **Settings / Config**: Per-repo configuration panel — CC threshold slider, toggle Bandit checks on/off, select LLM model, manage webhook URLs, and API token rotation.
- **Activity Log**: Audit trail of every action geekPR has taken — webhook received, job enqueued, review posted, errors encountered.

### Design Direction

Dark-mode-first with a terminal/hacker aesthetic. Monospace display font for headings and code. Neon green and amber accents on a near-black background. Subtle scanline or noise texture overlays for atmosphere. Sharp, geometric card layouts with glowing borders on hover. The vibe: "a senior engineer's command center."

## 7. Security

- **Webhook Signature Verification**: Every incoming payload must be verified against the `X-Hub-Signature-256` header using HMAC-SHA256 with the webhook secret. Reject unsigned or invalid payloads with `401`.
- **Token Scoping**: GitHub App installation tokens should use the minimum required permissions (pull request read/write, contents read).
- **No Secrets in Code**: All tokens, keys, and secrets live in `.env` (gitignored) and are loaded via Pydantic Settings.
- **Input Sanitization**: Never pass raw user-controlled strings (PR titles, branch names) directly into shell commands or LLM prompts without sanitization.

## 8. Async Processing

GitHub webhooks have a **10-second timeout**. Large PRs with many changed functions will easily exceed this if processed synchronously.

- **Architecture**: FastAPI webhook handler validates the payload, enqueues a Celery task, and returns `202 Accepted`.
- **Worker**: A Celery worker picks up the job, clones the diff, runs analysis, calls the LLM, and posts the review.
- **Broker**: Redis as the message broker (lightweight, easy to self-host).
- **Retry Logic**: Failed jobs retry up to 3 times with exponential backoff.
- **Status Tracking**: Job status (queued → processing → complete → failed) is stored in the database and exposed via a REST endpoint for the dashboard.

## 9. Multi-Repo & Configurable Rules

- **Multi-Repo Support**: geekPR installs as a GitHub App across an entire org. Each repo gets its own configuration record in the database.
- **Per-Repo Config**:
  - Cyclomatic Complexity threshold (default: 10)
  - Bandit checks enabled/disabled
  - **LLM provider**: `openai` or `ollama` (toggleable in dashboard Settings page)
  - LLM model override (e.g., `gpt-4o` for OpenAI, `codellama` for Ollama)
  - Auto-post reviews vs. queue for human approval
  - File/path exclusion patterns (e.g., ignore `**/migrations/**`)
- **Config Source**: Optionally read from a `.geekpr.yml` file in the repo root, with dashboard settings as fallback.

## 10. Deployment

- **Docker Compose**: Single `docker-compose.yml` that spins up all services:
  - `redis` — Message broker (Redis 7 Alpine, port 6379, with healthcheck)
  - `db` — PostgreSQL 16 Alpine (user: `geekpr`, port 5432, with healthcheck and persistent volume)
  - `backend` — FastAPI on port 8000, depends on redis + db, hot-reload via volume mount
  - `worker` — Celery worker using the same backend image, same env/deps
  - `frontend` — Next.js on port 3000, depends on backend
  - `caddy` (optional) — Reverse proxy for HTTPS termination (`/api/*` → backend, `/` → frontend)
- **Dockerfiles**:
  - `backend/Dockerfile` — Python 3.12 slim, pip install, uvicorn CMD
  - `frontend/Dockerfile` — Multi-stage Node 20 Alpine: build then run
- **Environment**: All config via `.env` file with a `.env.example` template checked into the repo. Docker Compose overrides `DATABASE_URL` and `REDIS_URL` to point at container hostnames.
- **Reverse Proxy**: Caddy for HTTPS termination and routing (`/api` → FastAPI, `/` → Next.js). Caddyfile in project root.
- **Health Checks**: `/health` endpoint on backend. Redis and PostgreSQL have container-level healthchecks with `condition: service_healthy`.
- **Volumes**: `pg_data` for PostgreSQL, `redis_data` for Redis snapshots, `caddy_data` for TLS certs.
- **Launch**: `docker compose up --build` from project root. All services start in dependency order.

## 11. Testing Strategy

- **Unit Tests**: pytest for all core logic — diff parsing, complexity calculation, Pydantic schema validation, LLM prompt construction.
- **Integration Tests**: Mock the GitHub API (using `respx` or `responses`) to test the full webhook → analyze → post-review pipeline.
- **LLM Tests**: Snapshot tests that verify the LLM prompt format and validate structured output parsing against known good/bad responses.
- **Frontend Tests**: Playwright for E2E flows (login → view feed → drill into review → change settings). Vitest for component unit tests.
- **CI**: GitHub Actions workflow that runs the full test suite on every PR (dogfooding — geekPR reviews its own PRs).