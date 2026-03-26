# geekPR — The Autonomous Code Reviewer

A self-hosted GitHub App that intercepts Pull Requests, performs static complexity analysis, and uses an LLM (OpenAI API or local Ollama) to suggest refactors for "smelly" code directly in PR comments.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose (optional, for containerized deployment)
- Redis (for async task queue)
- PostgreSQL (for production; SQLite for dev)
- Ollama (for local LLM inference) **or** an OpenAI API key

### Local Development (Without Docker)

1. **Backend setup**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with GitHub App credentials
   alembic upgrade head
   ```

2. **Start Redis**:
   ```bash
   redis-server
   ```

3. **Start Ollama** (if using local LLM — skip if using OpenAI):
   ```bash
   ollama serve
   ollama pull codellama
   ```

4. **Start the backend** (in another terminal):
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --reload --port 8000
   ```

5. **Start the Celery worker** (in another terminal):
   ```bash
   cd backend
   source venv/bin/activate
   celery -A app.tasks.celery_app worker --loglevel=info
   ```

6. **Frontend setup** (in another terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

7. **Access the dashboard**: http://localhost:3000

### Docker Deployment

```bash
docker compose up --build
```

This spins up:
- Redis (port 6379)
- PostgreSQL (port 5432)
- FastAPI backend (port 8000)
- Celery worker
- Next.js frontend (port 3000)

Access the dashboard at http://localhost:3000.

## Configuration

### GitHub App Setup

See `DOCS/PHASE_6_GITHUB_SETUP.md` for detailed instructions on:
1. Registering a GitHub App
2. Generating and storing the private key
3. Installing the app on repositories
4. Testing with ngrok for local development

### Environment Variables

**Backend** (`.env`):
```env
GITHUB_APP_ID=your-app-id
GITHUB_PRIVATE_KEY_PATH=./keys/geekpr.pem
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# LLM Provider: "openai" or "ollama"
DEFAULT_LLM_PROVIDER=ollama

# OpenAI API (or any OpenAI-compatible endpoint)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# Ollama (local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama

REDIS_URL=redis://localhost:6379/0
DATABASE_URL=sqlite:///./geekpr.db
DEFAULT_CC_THRESHOLD=10
```

**Frontend** (`.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

## Architecture

### Backend

- **FastAPI**: REST API and webhook listener
- **Celery + Redis**: Async task queue for PR analysis
- **SQLAlchemy**: Database ORM
- **Radon**: Cyclomatic complexity analysis
- **Bandit**: Security scanning
- **Instructor + OpenAI/Ollama**: Structured LLM output (switchable per-repo)

### Frontend

- **Next.js**: React framework
- **TailwindCSS**: Utility-first styling
- **Lucide**: Icon library
- **Recharts**: Data visualization
- **TanStack Query**: Server state management

## API Endpoints

### Webhooks
- `POST /api/webhook/github` — GitHub webhook listener

### Reviews
- `GET /api/reviews/` — List all reviews
- `GET /api/reviews/{id}` — Get a specific review

### Configuration
- `GET /api/config/{owner}/{repo}` — Get repo config
- `PUT /api/config/{owner}/{repo}` — Update repo config

### Jobs
- `GET /api/jobs/` — List analysis jobs

### Health
- `GET /health` — Backend health check

## Dashboard Pages

- **Feed** (`/`) — Real-time stream of analyzed PRs
- **Analytics** (`/analytics`) — Code quality trends and metrics
- **Activity** (`/activity`) — Audit trail of all actions
- **Settings** (`/settings`) — Per-repo configuration (LLM provider toggle, model, thresholds)

## Troubleshooting

### PR not being analyzed?

1. Check webhook deliveries: GitHub App → Settings → Webhook deliveries
2. Verify backend is running: `curl http://localhost:8000/health`
3. Check Celery worker: `celery -A app.tasks.celery_app worker --loglevel=info`
4. Verify Redis: `redis-cli ping` should return `PONG`

### LLM returning garbage?

**If using Ollama:**
1. Test Ollama: `curl http://localhost:11434/api/tags`
2. Try a different model: `ollama pull deepseek-coder`

**If using OpenAI:**
1. Verify your API key: `curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models`
2. Check `OPENAI_BASE_URL` is correct (default: `https://api.openai.com/v1`)
3. Try a different model (e.g., `gpt-4o-mini` for faster/cheaper results)

**General:**
1. Check the LLM prompt in `app/services/llm.py`
2. Switch provider per-repo in the Settings page

### Reviews not posting to GitHub?

1. Verify GitHub App permissions (Pull requests: Read & Write)
2. Check the installation ID in webhook payload
3. Verify the access token: `curl -H "Authorization: token $TOKEN" https://api.github.com/user`

## Testing

### Unit Tests
```bash
cd backend
pytest tests/unit/ -v
```

### Integration Tests
```bash
cd backend
pytest tests/integration/ -v
```

### Frontend E2E Tests
```bash
cd frontend
npm run test:e2e
```

## Deployment

### Docker Compose (Development)
```bash
docker compose up --build
```

### Production Deployment

1. Use PostgreSQL instead of SQLite
2. Set `DATABASE_URL=postgresql://user:pass@host:5432/geekpr`
3. Use a reverse proxy (Caddy, Traefik, or Nginx) for HTTPS
4. Store secrets in environment variables, not `.env`
5. Run database migrations: `alembic upgrade head`
6. Scale Celery workers as needed
7. Set `DEFAULT_LLM_PROVIDER=openai` and configure `OPENAI_API_KEY` for production-grade results
8. For Docker + Ollama on host, `OLLAMA_BASE_URL` defaults to `http://host.docker.internal:11434`

## Documentation

- `DOCS/THE_PLAN.md` — Full project specification
- `DOCS/THE_STEPS.md` — Implementation guide (8 phases)
- `DOCS/THE_CONTEXT.md` — Design decisions and gotchas
- `DOCS/PHASE_6_GITHUB_SETUP.md` — GitHub App registration

## License

MIT

## Contributing

Contributions welcome. Please follow the existing code style and add tests for new features.
