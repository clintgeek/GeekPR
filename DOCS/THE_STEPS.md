# geekPR — Implementation Steps

A step-by-step guide to building geekPR from zero to deployed. Each phase builds on the last. Complete them in order. Don't skip ahead.

---

## Phase 1: Project Scaffolding

Everything starts here. You're setting up the folder structure, virtual environment, and dependency files so the rest of the project has a home.

### Step 1.1 — Create the monorepo folder structure

From the project root (`geekPR/`), create the following directories:

```
geekPR/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI route handlers
│   │   ├── core/           # Config, security, constants
│   │   ├── models/         # SQLAlchemy database models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Business logic (analysis, LLM, GitHub)
│   │   ├── tasks/          # Celery task definitions
│   │   └── utils/          # Shared helpers
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # Next.js dashboard (created in Phase 5)
├── DOCS/
├── docker-compose.yml
├── .gitignore
└── README.md
```

Run these commands from the project root:

```bash
mkdir -p backend/app/{api,core,models,schemas,services,tasks,utils}
mkdir -p backend/tests/{unit,integration}
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/core/__init__.py
touch backend/app/models/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/services/__init__.py
touch backend/app/tasks/__init__.py
touch backend/app/utils/__init__.py
```

### Step 1.2 — Set up the Python virtual environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### Step 1.3 — Create `requirements.txt`

Create `backend/requirements.txt` with these exact contents:

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pygithub>=2.3.0
radon>=6.0.0
bandit>=1.7.0
instructor>=1.3.0
openai>=1.40.0
celery[redis]>=5.4.0
redis>=5.0.0
sqlalchemy>=2.0.0
alembic>=1.13.0
pydantic>=2.8.0
pydantic-settings>=2.4.0
python-dotenv>=1.0.0
httpx>=0.27.0
unidiff>=0.7.0
pytest>=8.3.0
pytest-asyncio>=0.24.0
respx>=0.21.0
```

Install them:

```bash
pip install -r requirements.txt
```

### Step 1.4 — Create `.env.example`

Create `backend/.env.example`. This is the template others will copy to `.env`:

```env
# GitHub App credentials
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY_PATH=
GITHUB_WEBHOOK_SECRET=

# LLM Provider: "openai" or "ollama"
DEFAULT_LLM_PROVIDER=ollama

# OpenAI API (or any OpenAI-compatible endpoint)
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# Ollama (local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama

# Redis
REDIS_URL=redis://localhost:6379/0

# Database
DATABASE_URL=sqlite:///./geekpr.db

# Complexity threshold (default)
DEFAULT_CC_THRESHOLD=10
```

**Important**: Copy this file to `.env` and fill in real values. Never commit `.env` to git.

```bash
cp .env.example .env
```

### Step 1.5 — Create `.gitignore`

Add to the project root `.gitignore`:

```
# Python
__pycache__/
*.pyc
venv/
*.egg-info/

# Environment
.env
*.pem

# Database
*.db

# Node
node_modules/
.next/

# IDE
.vscode/
.idea/

# OS
.DS_Store
```

### Step 1.6 — Verify

At this point you should be able to run:

```bash
python -c "import fastapi; print(fastapi.__version__)"
```

If it prints a version number, Phase 1 is complete.

---

## Phase 2: Configuration & Database

### Step 2.1 — Create the settings module

Create `backend/app/core/config.py`:

```python
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
```

**What this does**: Pydantic Settings automatically reads values from the `.env` file and environment variables. You import `settings` anywhere you need config values. No hardcoded secrets, ever. The `default_llm_provider` setting controls which LLM backend is used globally — `"ollama"` for local inference or `"openai"` for the OpenAI API (or any OpenAI-compatible endpoint like Azure, Together, etc.). Each repo can override this in the dashboard.

### Step 2.2 — Create the database models

Create `backend/app/models/database.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}  # SQLite only
    if "sqlite" in settings.database_url
    else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Create `backend/app/models/review.py`:

```python
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Enum
from sqlalchemy.sql import func

from app.models.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    repo_full_name = Column(String, index=True)          # e.g. "octocat/Hello-World"
    pr_number = Column(Integer)
    pr_title = Column(String)
    function_name = Column(String)
    file_path = Column(String)
    line_number = Column(Integer)
    complexity_score = Column(Float)
    suggestion = Column(Text)
    priority = Column(String, default="Medium")           # High / Medium / Low
    status = Column(String, default="pending")            # pending / posted / error
    created_at = Column(DateTime, server_default=func.now())
```

Create `backend/app/models/repo_config.py`:

```python
from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.models.database import Base


class RepoConfig(Base):
    __tablename__ = "repo_configs"

    id = Column(Integer, primary_key=True, index=True)
    repo_full_name = Column(String, unique=True, index=True)
    cc_threshold = Column(Integer, default=10)
    bandit_enabled = Column(Boolean, default=True)
    llm_provider = Column(String, default="ollama")    # "openai" or "ollama"
    llm_model = Column(String, default="codellama")
    auto_post = Column(Boolean, default=True)
    exclude_patterns = Column(Text, default="")           # comma-separated globs
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

Create `backend/app/models/job.py`:

```python
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.models.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    celery_task_id = Column(String, unique=True, index=True)
    repo_full_name = Column(String, index=True)
    pr_number = Column(Integer)
    status = Column(String, default="queued")             # queued / processing / complete / failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

### Step 2.3 — Initialize the database with Alembic

```bash
cd backend
alembic init alembic
```

Edit `backend/alembic/env.py` — find the line `target_metadata = None` and replace it with:

```python
from app.models.database import Base
from app.models.review import Review
from app.models.repo_config import RepoConfig
from app.models.job import Job

target_metadata = Base.metadata
```

Edit `backend/alembic.ini` — find the `sqlalchemy.url` line and set it to:

```
sqlalchemy.url = sqlite:///./geekpr.db
```

Generate and run the first migration:

```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

### Step 2.4 — Verify

```bash
python -c "from app.models.database import engine; from app.models.review import Review; print('Models loaded OK')"
```

---

## Phase 3: Core Backend Services

This is the brain of geekPR — the diff analyzer, complexity checker, and LLM integration.

### Step 3.1 — Webhook signature verification

Create `backend/app/core/security.py`:

```python
import hashlib
import hmac

from app.core.config import settings


def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify that the webhook payload was sent by GitHub.

    Args:
        payload_body: The raw bytes of the request body.
        signature_header: The value of the X-Hub-Signature-256 header.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not signature_header:
        return False

    expected_signature = (
        "sha256="
        + hmac.new(
            settings.github_webhook_secret.encode("utf-8"),
            msg=payload_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(expected_signature, signature_header)
```

**What this does**: GitHub sends a header called `X-Hub-Signature-256` with every webhook. It's a HMAC-SHA256 hash of the request body using your webhook secret. This function recomputes the hash and compares. If they don't match, someone is faking the request — reject it.

### Step 3.2 — Diff analyzer

Create `backend/app/services/diff_analyzer.py`:

```python
import re
from dataclasses import dataclass

from unidiff import PatchSet


@dataclass
class ChangedFunction:
    """Represents a function that was added or modified in a diff."""
    file_path: str
    function_name: str
    source_code: str
    start_line: int
    end_line: int


def extract_changed_functions(diff_text: str) -> list[ChangedFunction]:
    """
    Parse a unified diff and extract Python functions that were added or modified.

    Args:
        diff_text: The raw unified diff string from GitHub.

    Returns:
        A list of ChangedFunction objects.
    """
    patch = PatchSet(diff_text)
    changed_functions = []

    for patched_file in patch:
        # Only analyze Python files
        if not patched_file.path.endswith(".py"):
            continue

        # Collect all added/modified lines into a single string
        added_lines = []
        for hunk in patched_file:
            for line in hunk:
                if line.is_added:
                    added_lines.append((line.target_line_no, line.value))

        if not added_lines:
            continue

        # Rebuild the added code and find function definitions
        full_added_text = "\n".join(line_text for _, line_text in added_lines)

        # Regex to find function definitions
        # This is a simple approach — finds `def func_name(...):`
        func_pattern = re.compile(
            r"^([ \t]*)def\s+(\w+)\s*\(.*?\).*?:",
            re.MULTILINE,
        )

        for match in func_pattern.finditer(full_added_text):
            indent = match.group(1)
            func_name = match.group(2)
            func_start = match.start()

            # Find the end of the function by looking for the next line
            # with equal or less indentation (or end of text)
            remaining = full_added_text[match.end():]
            func_body_lines = []
            for body_line in remaining.split("\n"):
                # Empty lines are part of the function
                if body_line.strip() == "":
                    func_body_lines.append(body_line)
                    continue
                # If indentation is deeper than the def, it's still in the function
                if body_line.startswith(indent + " ") or body_line.startswith(indent + "\t"):
                    func_body_lines.append(body_line)
                else:
                    break

            func_source = full_added_text[func_start:match.end()] + "\n".join(func_body_lines)

            # Find the approximate line number
            start_line = added_lines[0][0] if added_lines else 0

            changed_functions.append(ChangedFunction(
                file_path=patched_file.path,
                function_name=func_name,
                source_code=func_source.strip(),
                start_line=start_line,
                end_line=start_line + len(func_body_lines),
            ))

    return changed_functions
```

**What this does**: Takes a raw unified diff (the text you see when you run `git diff`), parses it with the `unidiff` library, and extracts every Python function that was added or modified. This is what we feed into the complexity checker and LLM — we never analyze the whole file, just the changed functions.

### Step 3.3 — Complexity analyzer

Create `backend/app/services/complexity.py`:

```python
from dataclasses import dataclass

from radon.complexity import cc_visit


@dataclass
class ComplexityResult:
    """Result of analyzing a function's cyclomatic complexity."""
    function_name: str
    score: int
    rank: str       # A through F (A is simplest, F is most complex)
    is_flagged: bool


def analyze_complexity(source_code: str, threshold: int = 10) -> list[ComplexityResult]:
    """
    Calculate the Cyclomatic Complexity of all functions in the given source code.

    Args:
        source_code: A string of Python source code.
        threshold: Functions with CC above this are flagged.

    Returns:
        A list of ComplexityResult for every function found.
    """
    try:
        blocks = cc_visit(source_code)
    except SyntaxError:
        return []

    results = []
    for block in blocks:
        results.append(ComplexityResult(
            function_name=block.name,
            score=block.complexity,
            rank=block.letter,
            is_flagged=block.complexity > threshold,
        ))

    return results
```

**What this does**: Radon's `cc_visit` parses Python code and returns a complexity score for each function. A score of 1–5 is fine. 6–10 is getting messy. Above 10 is a "God Function" that should be refactored. The `threshold` is configurable per-repo.

### Step 3.4 — Bandit security scanner

Create `backend/app/services/security_scan.py`:

```python
import json
import subprocess
import tempfile
from dataclasses import dataclass


@dataclass
class SecurityIssue:
    """A security issue found by Bandit."""
    test_id: str        # e.g. "B105"
    description: str    # e.g. "Possible hardcoded password"
    severity: str       # LOW / MEDIUM / HIGH
    confidence: str     # LOW / MEDIUM / HIGH
    line_number: int


def run_bandit_scan(source_code: str) -> list[SecurityIssue]:
    """
    Run Bandit on a snippet of Python source code.

    Args:
        source_code: Python source code as a string.

    Returns:
        A list of SecurityIssue objects.
    """
    # Write the code to a temp file because Bandit operates on files
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(source_code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["bandit", "-f", "json", "-q", tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Bandit returns exit code 1 if issues are found (not an error)
        output = json.loads(result.stdout) if result.stdout else {"results": []}
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return []

    issues = []
    for item in output.get("results", []):
        issues.append(SecurityIssue(
            test_id=item.get("test_id", ""),
            description=item.get("issue_text", ""),
            severity=item.get("issue_severity", "LOW"),
            confidence=item.get("issue_confidence", "LOW"),
            line_number=item.get("line_number", 0),
        ))

    return issues
```

### Step 3.5 — LLM integration with Instructor

Create `backend/app/schemas/llm.py`:

```python
from pydantic import BaseModel, Field


class RefactorSuggestion(BaseModel):
    """Structured output the LLM must return."""
    summary: str = Field(description="One-sentence summary of the problem.")
    refactored_code: str = Field(description="The complete refactored function.")
    explanation: str = Field(description="Why this refactor improves the code.")
    priority: str = Field(
        default="Medium",
        description="Priority level: High, Medium, or Low.",
    )
```

Create `backend/app/services/llm.py`:

```python
import instructor
from openai import OpenAI

from app.core.config import settings
from app.schemas.llm import RefactorSuggestion


def get_llm_client(
    provider: str | None = None,
    model: str | None = None,
) -> tuple[instructor.Instructor, str]:
    """
    Create an Instructor-patched OpenAI client for the chosen provider.

    Args:
        provider: "openai" or "ollama". Falls back to settings.default_llm_provider.
        model: Model name override. Falls back to the provider's default.

    Returns:
        A tuple of (Instructor client, resolved model name).
    """
    provider = provider or settings.default_llm_provider

    if provider == "openai":
        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        resolved_model = model or settings.openai_model
    else:
        client = OpenAI(
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",
        )
        resolved_model = model or settings.ollama_model

    return instructor.from_openai(client), resolved_model


def request_refactor(
    function_source: str,
    complexity_score: int,
    function_name: str,
    provider: str | None = None,
    model: str | None = None,
) -> RefactorSuggestion:
    """
    Ask the LLM to suggest a refactor for a complex function.

    Args:
        function_source: The full source code of the function.
        complexity_score: The Cyclomatic Complexity score from Radon.
        function_name: The name of the function.
        provider: "openai" or "ollama". Falls back to env default.
        model: Model name override. Falls back to the provider's default.

    Returns:
        A RefactorSuggestion with structured fields.
    """
    client, resolved_model = get_llm_client(provider=provider, model=model)

    prompt = f"""Act as a Staff Engineer performing a code review.

The following function `{function_name}` has a Cyclomatic Complexity score of {complexity_score}, which exceeds the acceptable threshold.

```python
{function_source}
```

Refactor this function to be more modular, readable, and maintainable.
Requirements:
- Break complex conditionals into smaller helper functions.
- Add Type Hints to all parameters and return values.
- Add a Google-style Docstring.
- Keep the same external behavior (don't change the function signature).
"""

    response = client.chat.completions.create(
        model=resolved_model,
        response_model=RefactorSuggestion,
        messages=[{"role": "user", "content": prompt}],
        max_retries=2,
    )

    return response
```

**What this does**: We use the `openai` SDK which speaks the OpenAI-compatible API. Both OpenAI and Ollama support this protocol. `get_llm_client()` routes to the correct backend based on the `provider` parameter — `"openai"` uses your API key and custom base URL, `"ollama"` points at the local server. `instructor` wraps the client so the LLM is forced to return JSON matching our `RefactorSuggestion` Pydantic model. If the LLM hallucinates garbage, Instructor retries automatically. The provider and model are configurable per-repo via the dashboard Settings page.

### Step 3.6 — GitHub service

Create `backend/app/services/github_service.py`:

```python
from github import Github, GithubIntegration

from app.core.config import settings


def get_github_client(installation_id: int) -> Github:
    """
    Authenticate as a GitHub App installation and return a PyGithub client.

    Args:
        installation_id: The GitHub App installation ID from the webhook payload.

    Returns:
        An authenticated Github client scoped to that installation.
    """
    with open(settings.github_private_key_path, "r") as f:
        private_key = f.read()

    integration = GithubIntegration(
        integration_id=settings.github_app_id,
        private_key=private_key,
    )

    access_token = integration.get_access_token(installation_id).token
    return Github(access_token)


def get_pr_diff(github_client: Github, repo_full_name: str, pr_number: int) -> str:
    """
    Fetch the unified diff for a pull request.

    Args:
        github_client: An authenticated Github instance.
        repo_full_name: e.g. "octocat/Hello-World"
        pr_number: The PR number.

    Returns:
        The diff as a string.
    """
    repo = github_client.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)

    # PyGithub doesn't have a direct .diff property, so we use the raw API
    diff_url = pr.diff_url
    import httpx
    response = httpx.get(diff_url)
    return response.text


def post_review_comment(
    github_client: Github,
    repo_full_name: str,
    pr_number: int,
    file_path: str,
    line: int,
    body: str,
) -> None:
    """
    Post a review comment on a specific line of a PR.

    Args:
        github_client: An authenticated Github instance.
        repo_full_name: e.g. "octocat/Hello-World"
        pr_number: The PR number.
        file_path: The path to the file in the repo.
        line: The line number to comment on.
        body: The Markdown-formatted comment body.
    """
    repo = github_client.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    commit = pr.get_commits().reversed[0]  # Latest commit

    pr.create_review_comment(
        body=body,
        commit=commit,
        path=file_path,
        line=line,
    )


def format_review_comment(
    function_name: str,
    complexity_score: int,
    suggestion_summary: str,
    refactored_code: str,
    explanation: str,
    priority: str,
    security_issues: list[str] | None = None,
) -> str:
    """
    Build a nicely formatted Markdown comment for the PR.

    Returns:
        A Markdown string ready to post.
    """
    severity_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(priority, "⚪")

    comment = f"""## {severity_emoji} geekPR — Code Review

**Function**: `{function_name}`
**Cyclomatic Complexity**: {complexity_score}
**Priority**: {priority}

### Summary
{suggestion_summary}

### Suggested Refactor
```python
{refactored_code}
```

### Why?
{explanation}
"""

    if security_issues:
        comment += "\n### ⚠️ Security Concerns\n"
        for issue in security_issues:
            comment += f"- {issue}\n"

    comment += "\n---\n*Generated by [geekPR](https://github.com/your-org/geekPR) — The Autonomous Reviewer*"
    return comment
```

### Step 3.7 — Verify

Run a quick smoke test on the complexity analyzer:

```bash
cd backend
python -c "
from app.services.complexity import analyze_complexity
code = '''
def messy(x):
    if x > 0:
        if x > 10:
            if x > 100:
                return 'big'
            return 'medium'
        return 'small'
    return 'negative'
'''
results = analyze_complexity(code, threshold=3)
for r in results:
    print(f'{r.function_name}: CC={r.score} ({r.rank}) flagged={r.is_flagged}')
"
```

You should see output like: `messy: CC=4 (A) flagged=True`

---

## Phase 4: Celery Tasks & FastAPI Endpoints

### Step 4.1 — Celery app setup

Create `backend/app/tasks/celery_app.py`:

```python
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "geekpr",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,                 # Don't ack until task completes
    task_reject_on_worker_lost=True,     # Retry if worker crashes
    broker_connection_retry_on_startup=True,
)
```

### Step 4.2 — The main analysis task

Create `backend/app/tasks/analyze_pr.py`:

```python
from app.tasks.celery_app import celery_app
from app.services.diff_analyzer import extract_changed_functions
from app.services.complexity import analyze_complexity
from app.services.security_scan import run_bandit_scan
from app.services.llm import request_refactor
from app.services.github_service import (
    get_github_client,
    get_pr_diff,
    post_review_comment,
    format_review_comment,
)
from app.models.database import SessionLocal
from app.models.review import Review
from app.models.repo_config import RepoConfig
from app.models.job import Job


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # seconds
)
def analyze_pr_task(self, installation_id: int, repo_full_name: str, pr_number: int, pr_title: str):
    """
    The main Celery task. Runs the full pipeline:
    1. Fetch diff
    2. Extract functions
    3. Check complexity
    4. Run security scan
    5. Call LLM for flagged functions
    6. Post review comments
    7. Save results to DB
    """
    db = SessionLocal()

    try:
        # Update job status
        job = db.query(Job).filter_by(celery_task_id=self.request.id).first()
        if job:
            job.status = "processing"
            db.commit()

        # Load repo-specific config (or use defaults)
        repo_config = db.query(RepoConfig).filter_by(repo_full_name=repo_full_name).first()
        cc_threshold = repo_config.cc_threshold if repo_config else 10
        bandit_enabled = repo_config.bandit_enabled if repo_config else True
        llm_provider = repo_config.llm_provider if repo_config else None
        llm_model = repo_config.llm_model if repo_config else None
        auto_post = repo_config.auto_post if repo_config else True

        # 1. Get the diff from GitHub
        gh = get_github_client(installation_id)
        diff_text = get_pr_diff(gh, repo_full_name, pr_number)

        # 2. Extract changed functions
        functions = extract_changed_functions(diff_text)

        if not functions:
            if job:
                job.status = "complete"
                db.commit()
            return {"message": "No Python functions changed", "reviews": 0}

        reviews_posted = 0

        for func in functions:
            # 3. Check complexity
            complexity_results = analyze_complexity(func.source_code, threshold=cc_threshold)
            flagged = [r for r in complexity_results if r.is_flagged]

            if not flagged:
                continue

            # 4. Security scan (optional)
            security_issues = []
            if bandit_enabled:
                issues = run_bandit_scan(func.source_code)
                security_issues = [f"[{i.test_id}] {i.description} (severity: {i.severity})" for i in issues]

            # 5. Call the LLM
            for result in flagged:
                suggestion = request_refactor(
                    function_source=func.source_code,
                    complexity_score=result.score,
                    function_name=result.function_name,
                    provider=llm_provider,
                    model=llm_model,
                )

                # 6. Format and post comment
                comment_body = format_review_comment(
                    function_name=result.function_name,
                    complexity_score=result.score,
                    suggestion_summary=suggestion.summary,
                    refactored_code=suggestion.refactored_code,
                    explanation=suggestion.explanation,
                    priority=suggestion.priority,
                    security_issues=security_issues if security_issues else None,
                )

                if auto_post:
                    post_review_comment(
                        github_client=gh,
                        repo_full_name=repo_full_name,
                        pr_number=pr_number,
                        file_path=func.file_path,
                        line=func.start_line,
                        body=comment_body,
                    )

                # 7. Save to database
                review = Review(
                    repo_full_name=repo_full_name,
                    pr_number=pr_number,
                    pr_title=pr_title,
                    function_name=result.function_name,
                    file_path=func.file_path,
                    line_number=func.start_line,
                    complexity_score=result.score,
                    suggestion=comment_body,
                    priority=suggestion.priority,
                    status="posted" if auto_post else "pending",
                )
                db.add(review)
                reviews_posted += 1

        db.commit()

        # Update job status
        if job:
            job.status = "complete"
            db.commit()

        return {"message": f"Analyzed {len(functions)} functions", "reviews": reviews_posted}

    except Exception as exc:
        db.rollback()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc)

    finally:
        db.close()
```

**What this does**: This is the entire pipeline from THE_PLAN.md, sections 4–5, implemented as a single Celery task. It runs asynchronously so the webhook can return immediately.

### Step 4.3 — FastAPI application and webhook endpoint

Create `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.webhook import router as webhook_router
from app.api.reviews import router as reviews_router
from app.api.config import router as config_router
from app.api.jobs import router as jobs_router
from app.models.database import Base, engine

# Create all tables (for dev — use Alembic migrations in prod)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="geekPR",
    description="The Autonomous Code Reviewer",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, prefix="/api/webhook", tags=["webhook"])
app.include_router(reviews_router, prefix="/api/reviews", tags=["reviews"])
app.include_router(config_router, prefix="/api/config", tags=["config"])
app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "geekpr-backend"}
```

### Step 4.4 — Webhook route

Create `backend/app/api/webhook.py`:

```python
from fastapi import APIRouter, Request, HTTPException

from app.core.security import verify_webhook_signature
from app.tasks.analyze_pr import analyze_pr_task
from app.models.database import SessionLocal
from app.models.job import Job

router = APIRouter()


@router.post("/github")
async def handle_github_webhook(request: Request):
    """
    Receives GitHub webhook events for pull_request actions.
    Validates the signature, enqueues the analysis task, and returns 202.
    """
    # 1. Verify signature
    payload_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_webhook_signature(payload_body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 2. Parse payload
    payload = await request.json()

    # Only process opened or synchronized (new commits pushed) PRs
    action = payload.get("action")
    if action not in ("opened", "synchronize"):
        return {"message": f"Ignored action: {action}"}

    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    installation = payload.get("installation", {})

    repo_full_name = repo.get("full_name")
    pr_number = pr.get("number")
    pr_title = pr.get("title", "")
    installation_id = installation.get("id")

    if not all([repo_full_name, pr_number, installation_id]):
        raise HTTPException(status_code=400, detail="Missing required payload fields")

    # 3. Enqueue the Celery task
    task = analyze_pr_task.delay(
        installation_id=installation_id,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        pr_title=pr_title,
    )

    # 4. Save job record
    db = SessionLocal()
    try:
        job = Job(
            celery_task_id=task.id,
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            status="queued",
        )
        db.add(job)
        db.commit()
    finally:
        db.close()

    # 5. Return immediately
    return {"message": "Analysis enqueued", "task_id": task.id}
```

### Step 4.5 — REST API routes for the dashboard

Create `backend/app/api/reviews.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.review import Review

router = APIRouter()


@router.get("/")
def list_reviews(
    repo: str | None = None,
    status: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List reviews with optional filters."""
    query = db.query(Review).order_by(Review.created_at.desc())

    if repo:
        query = query.filter(Review.repo_full_name == repo)
    if status:
        query = query.filter(Review.status == status)

    total = query.count()
    reviews = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "reviews": [
            {
                "id": r.id,
                "repo": r.repo_full_name,
                "pr_number": r.pr_number,
                "pr_title": r.pr_title,
                "function_name": r.function_name,
                "file_path": r.file_path,
                "line_number": r.line_number,
                "complexity_score": r.complexity_score,
                "suggestion": r.suggestion,
                "priority": r.priority,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reviews
        ],
    }


@router.get("/{review_id}")
def get_review(review_id: int, db: Session = Depends(get_db)):
    """Get a single review by ID."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Review not found")

    return {
        "id": review.id,
        "repo": review.repo_full_name,
        "pr_number": review.pr_number,
        "pr_title": review.pr_title,
        "function_name": review.function_name,
        "file_path": review.file_path,
        "line_number": review.line_number,
        "complexity_score": review.complexity_score,
        "suggestion": review.suggestion,
        "priority": review.priority,
        "status": review.status,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }
```

Create `backend/app/api/config.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.repo_config import RepoConfig

router = APIRouter()


class RepoConfigUpdate(BaseModel):
    cc_threshold: int | None = None
    bandit_enabled: bool | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    auto_post: bool | None = None
    exclude_patterns: str | None = None


@router.get("/{repo_owner}/{repo_name}")
def get_repo_config(repo_owner: str, repo_name: str, db: Session = Depends(get_db)):
    """Get configuration for a specific repo."""
    full_name = f"{repo_owner}/{repo_name}"
    config = db.query(RepoConfig).filter_by(repo_full_name=full_name).first()

    if not config:
        # Return defaults
        return {
            "repo": full_name,
            "cc_threshold": 10,
            "bandit_enabled": True,
            "llm_provider": "ollama",
            "llm_model": "codellama",
            "auto_post": True,
            "exclude_patterns": "",
        }

    return {
        "repo": config.repo_full_name,
        "cc_threshold": config.cc_threshold,
        "bandit_enabled": config.bandit_enabled,
        "llm_provider": config.llm_provider,
        "llm_model": config.llm_model,
        "auto_post": config.auto_post,
        "exclude_patterns": config.exclude_patterns,
    }


@router.put("/{repo_owner}/{repo_name}")
def update_repo_config(
    repo_owner: str,
    repo_name: str,
    update: RepoConfigUpdate,
    db: Session = Depends(get_db),
):
    """Create or update configuration for a repo."""
    full_name = f"{repo_owner}/{repo_name}"
    config = db.query(RepoConfig).filter_by(repo_full_name=full_name).first()

    if not config:
        config = RepoConfig(repo_full_name=full_name)
        db.add(config)

    if update.cc_threshold is not None:
        config.cc_threshold = update.cc_threshold
    if update.bandit_enabled is not None:
        config.bandit_enabled = update.bandit_enabled
    if update.llm_provider is not None:
        config.llm_provider = update.llm_provider
    if update.llm_model is not None:
        config.llm_model = update.llm_model
    if update.auto_post is not None:
        config.auto_post = update.auto_post
    if update.exclude_patterns is not None:
        config.exclude_patterns = update.exclude_patterns

    db.commit()
    return {"message": "Config updated", "repo": full_name}
```

Create `backend/app/api/jobs.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.job import Job

router = APIRouter()


@router.get("/")
def list_jobs(
    repo: str | None = None,
    status: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List jobs with optional filters."""
    query = db.query(Job).order_by(Job.created_at.desc())

    if repo:
        query = query.filter(Job.repo_full_name == repo)
    if status:
        query = query.filter(Job.status == status)

    total = query.count()
    jobs = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "jobs": [
            {
                "id": j.id,
                "celery_task_id": j.celery_task_id,
                "repo": j.repo_full_name,
                "pr_number": j.pr_number,
                "status": j.status,
                "error_message": j.error_message,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ],
    }
```

### Step 4.6 — Run the backend

You need **three terminal windows**:

**Terminal 1 — Redis** (install if needed: `sudo apt install redis-server`):

```bash
redis-server
```

**Terminal 2 — Celery worker**:

```bash
cd backend
source venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info
```

**Terminal 3 — FastAPI dev server**:

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Step 4.7 — Verify

Open your browser to `http://localhost:8000/health`. You should see:

```json
{"status": "ok", "service": "geekpr-backend"}
```

Also check `http://localhost:8000/docs` — FastAPI auto-generates Swagger UI showing all your endpoints.

---

## Phase 5: Frontend Dashboard

### Step 5.1 — Scaffold the Next.js app

From the project root:

```bash
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*"
```

Accept all defaults when prompted.

### Step 5.2 — Install dependencies

```bash
cd frontend
npm install @tanstack/react-query recharts lucide-react
npx shadcn@latest init
```

When `shadcn init` asks:
- Style: **New York**
- Base color: **Zinc** (closest to our dark hacker theme)
- CSS variables: **Yes**

Then install the components you'll need:

```bash
npx shadcn@latest add card badge button table tabs slider switch select separator scroll-area
```

### Step 5.3 — Configure the global theme

Replace the contents of `frontend/src/app/globals.css` with the dark terminal aesthetic. Key design tokens:

```css
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: #0a0a0a;
  --color-foreground: #e0e0e0;
  --color-card: #111111;
  --color-card-foreground: #e0e0e0;
  --color-popover: #111111;
  --color-popover-foreground: #e0e0e0;
  --color-primary: #39ff14;
  --color-primary-foreground: #0a0a0a;
  --color-secondary: #1a1a1a;
  --color-secondary-foreground: #e0e0e0;
  --color-muted: #1a1a1a;
  --color-muted-foreground: #777777;
  --color-accent: #ffbf00;
  --color-accent-foreground: #0a0a0a;
  --color-destructive: #ff3333;
  --color-destructive-foreground: #e0e0e0;
  --color-border: #222222;
  --color-input: #1a1a1a;
  --color-ring: #39ff14;
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;

  --font-sans: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, monospace;
}

body {
  background-color: var(--color-background);
  color: var(--color-foreground);
  font-family: var(--font-sans);
}

/* Scanline overlay for atmosphere */
body::after {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.03) 2px,
    rgba(0, 0, 0, 0.03) 4px
  );
}
```

**What this does**: Sets up a near-black background (`#0a0a0a`), neon green primary (`#39ff14`), amber accent (`#ffbf00`), and adds a subtle CRT scanline overlay. The font stack uses IBM Plex — a clean, modern monospace + sans pairing.

### Step 5.4 — Add Google Fonts

Edit `frontend/src/app/layout.tsx` to load IBM Plex fonts. Add to the `<head>`:

```tsx
import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "geekPR — The Autonomous Reviewer",
  description: "AI-powered code review dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${plexSans.variable} ${plexMono.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
```

### Step 5.5 — Create the API client

Create `frontend/src/lib/api.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export const api = {
  // Reviews
  getReviews: (params?: { repo?: string; status?: string; skip?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.repo) query.set("repo", params.repo);
    if (params?.status) query.set("status", params.status);
    if (params?.skip) query.set("skip", String(params.skip));
    if (params?.limit) query.set("limit", String(params.limit));
    return fetchAPI<any>(`/reviews/?${query}`);
  },

  getReview: (id: number) => fetchAPI<any>(`/reviews/${id}`),

  // Jobs
  getJobs: (params?: { repo?: string; status?: string }) => {
    const query = new URLSearchParams();
    if (params?.repo) query.set("repo", params.repo);
    if (params?.status) query.set("status", params.status);
    return fetchAPI<any>(`/jobs/?${query}`);
  },

  // Config
  getRepoConfig: (owner: string, name: string) =>
    fetchAPI<any>(`/config/${owner}/${name}`),

  updateRepoConfig: (owner: string, name: string, config: any) =>
    fetchAPI<any>(`/config/${owner}/${name}`, {
      method: "PUT",
      body: JSON.stringify(config),
    }),
};
```

### Step 5.6 — Set up TanStack Query provider

Create `frontend/src/components/providers.tsx`:

```tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 10_000,     // 10 seconds
            refetchInterval: 30_000, // Poll every 30 seconds
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

Then wrap your layout body with it in `layout.tsx`:

```tsx
import { Providers } from "@/components/providers";

// ... inside RootLayout return:
<body className={`${plexSans.variable} ${plexMono.variable} antialiased`}>
  <Providers>{children}</Providers>
</body>
```

### Step 5.7 — Build the sidebar layout

Create `frontend/src/components/sidebar.tsx`:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  GitPullRequest,
  BarChart3,
  Settings,
  Activity,
  Terminal,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Feed", icon: GitPullRequest },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-56 border-r border-border bg-card flex flex-col">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-5 border-b border-border">
        <Terminal className="h-5 w-5 text-primary" />
        <span className="font-mono text-lg font-semibold tracking-tight text-primary">
          geekPR
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-border px-4 py-3">
        <p className="font-mono text-xs text-muted-foreground">v0.1.0</p>
      </div>
    </aside>
  );
}
```

### Step 5.8 — Build the PR Review Feed page (Home)

Replace `frontend/src/app/page.tsx`:

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Sidebar } from "@/components/sidebar";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  GitPullRequest,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
} from "lucide-react";

const priorityColors: Record<string, string> = {
  High: "bg-destructive/20 text-destructive border-destructive/30",
  Medium: "bg-accent/20 text-accent border-accent/30",
  Low: "bg-primary/20 text-primary border-primary/30",
};

const statusIcons: Record<string, any> = {
  pending: Clock,
  posted: CheckCircle2,
  error: AlertTriangle,
};

export default function FeedPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["reviews"],
    queryFn: () => api.getReviews({ limit: 50 }),
  });

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-56 p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-mono text-2xl font-bold text-foreground">
            PR Review Feed
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time stream of analyzed pull requests
          </p>
        </div>

        {/* Content */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        )}

        {error && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 p-4">
            <p className="text-sm text-destructive">
              Failed to load reviews. Is the backend running?
            </p>
          </div>
        )}

        {data && data.reviews.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <GitPullRequest className="h-10 w-10 mb-3 opacity-40" />
            <p className="text-sm">No reviews yet. Push a PR to get started.</p>
          </div>
        )}

        {data && (
          <div className="grid gap-4">
            {data.reviews.map((review: any) => {
              const StatusIcon = statusIcons[review.status] || Clock;
              return (
                <Card
                  key={review.id}
                  className="group border-border bg-card p-5 transition-all hover:border-primary/40 hover:shadow-[0_0_15px_rgba(57,255,20,0.05)]"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      {/* Repo + PR */}
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-mono text-xs text-muted-foreground">
                          {review.repo}
                        </span>
                        <span className="text-muted-foreground/40">•</span>
                        <span className="font-mono text-xs text-primary">
                          #{review.pr_number}
                        </span>
                      </div>

                      {/* Function name */}
                      <h3 className="font-mono text-sm font-semibold text-foreground truncate">
                        {review.function_name}
                      </h3>
                      <p className="text-xs text-muted-foreground mt-1">
                        {review.file_path}:{review.line_number}
                      </p>
                    </div>

                    {/* Right side — score + badges */}
                    <div className="flex items-center gap-3 ml-4">
                      <div className="text-right">
                        <p className="font-mono text-2xl font-bold text-foreground">
                          {review.complexity_score}
                        </p>
                        <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                          CC Score
                        </p>
                      </div>
                      <Badge
                        variant="outline"
                        className={priorityColors[review.priority] || ""}
                      >
                        {review.priority}
                      </Badge>
                      <StatusIcon className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
```

### Step 5.9 — Build the Analytics page

Create `frontend/src/app/analytics/page.tsx`:

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Sidebar } from "@/components/sidebar";
import { Card } from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import { BarChart3, TrendingDown, AlertTriangle, CheckCircle2 } from "lucide-react";

export default function AnalyticsPage() {
  const { data } = useQuery({
    queryKey: ["reviews", "analytics"],
    queryFn: () => api.getReviews({ limit: 100 }),
  });

  // Compute stats from review data
  const reviews = data?.reviews || [];
  const totalReviews = reviews.length;
  const avgComplexity =
    reviews.length > 0
      ? (reviews.reduce((sum: number, r: any) => sum + r.complexity_score, 0) / reviews.length).toFixed(1)
      : "0";
  const highPriority = reviews.filter((r: any) => r.priority === "High").length;
  const posted = reviews.filter((r: any) => r.status === "posted").length;

  // Group by file for bar chart
  const fileCounts: Record<string, number> = {};
  reviews.forEach((r: any) => {
    const short = r.file_path?.split("/").pop() || "unknown";
    fileCounts[short] = (fileCounts[short] || 0) + 1;
  });
  const fileData = Object.entries(fileCounts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  // Group by date for line chart
  const dateCounts: Record<string, { date: string; avgCC: number; count: number; total: number }> = {};
  reviews.forEach((r: any) => {
    const date = r.created_at?.split("T")[0] || "unknown";
    if (!dateCounts[date]) dateCounts[date] = { date, avgCC: 0, count: 0, total: 0 };
    dateCounts[date].total += r.complexity_score;
    dateCounts[date].count += 1;
  });
  const trendData = Object.values(dateCounts)
    .map((d) => ({ ...d, avgCC: +(d.total / d.count).toFixed(1) }))
    .sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-56 p-8">
        <div className="mb-8">
          <h1 className="font-mono text-2xl font-bold text-foreground">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Code quality trends and review metrics
          </p>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {[
            { label: "Total Reviews", value: totalReviews, icon: BarChart3, color: "text-primary" },
            { label: "Avg Complexity", value: avgComplexity, icon: TrendingDown, color: "text-accent" },
            { label: "High Priority", value: highPriority, icon: AlertTriangle, color: "text-destructive" },
            { label: "Posted", value: posted, icon: CheckCircle2, color: "text-primary" },
          ].map((stat) => (
            <Card key={stat.label} className="border-border bg-card p-5">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs uppercase tracking-wider text-muted-foreground">{stat.label}</p>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </div>
              <p className="font-mono text-3xl font-bold text-foreground">{stat.value}</p>
            </Card>
          ))}
        </div>

        {/* Charts */}
        <div className="grid grid-cols-2 gap-4">
          {/* Complexity trend */}
          <Card className="border-border bg-card p-5">
            <h3 className="font-mono text-sm font-semibold mb-4">Complexity Trend</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                <XAxis dataKey="date" tick={{ fill: "#777", fontSize: 11 }} />
                <YAxis tick={{ fill: "#777", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#111", border: "1px solid #222", borderRadius: "6px" }}
                  labelStyle={{ color: "#777" }}
                />
                <Line type="monotone" dataKey="avgCC" stroke="#39ff14" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          {/* Most flagged files */}
          <Card className="border-border bg-card p-5">
            <h3 className="font-mono text-sm font-semibold mb-4">Most Flagged Files</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={fileData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                <XAxis type="number" tick={{ fill: "#777", fontSize: 11 }} />
                <YAxis dataKey="name" type="category" tick={{ fill: "#777", fontSize: 11 }} width={120} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#111", border: "1px solid #222", borderRadius: "6px" }}
                  labelStyle={{ color: "#777" }}
                />
                <Bar dataKey="count" fill="#ffbf00" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      </main>
    </div>
  );
}
```

### Step 5.10 — Build the Activity Log page

Create `frontend/src/app/activity/page.tsx`:

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Sidebar } from "@/components/sidebar";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, XCircle, Clock, Cog } from "lucide-react";

const statusConfig: Record<string, { icon: any; color: string }> = {
  queued: { icon: Clock, color: "text-muted-foreground" },
  processing: { icon: Cog, color: "text-accent" },
  complete: { icon: CheckCircle2, color: "text-primary" },
  failed: { icon: XCircle, color: "text-destructive" },
};

export default function ActivityPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.getJobs(),
  });

  const jobs = data?.jobs || [];

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-56 p-8">
        <div className="mb-8">
          <h1 className="font-mono text-2xl font-bold text-foreground">Activity Log</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Audit trail of every webhook, job, and review action
          </p>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        )}

        <div className="space-y-2">
          {jobs.map((job: any) => {
            const config = statusConfig[job.status] || statusConfig.queued;
            const Icon = config.icon;
            return (
              <div
                key={job.id}
                className="flex items-center gap-4 rounded-md border border-border bg-card px-4 py-3"
              >
                <Icon className={`h-4 w-4 ${config.color}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-foreground">{job.repo}</span>
                    <span className="font-mono text-xs text-primary">#{job.pr_number}</span>
                  </div>
                  {job.error_message && (
                    <p className="text-xs text-destructive mt-1 truncate">{job.error_message}</p>
                  )}
                </div>
                <Badge variant="outline" className="font-mono text-xs">
                  {job.status}
                </Badge>
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  {job.created_at ? new Date(job.created_at).toLocaleString() : "—"}
                </span>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
```

### Step 5.11 — Build the Settings page

Create `frontend/src/app/settings/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [repoInput, setRepoInput] = useState("");
  const [config, setConfig] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function loadConfig() {
    const parts = repoInput.split("/");
    if (parts.length !== 2) return;
    const data = await api.getRepoConfig(parts[0], parts[1]);
    setConfig(data);
  }

  async function saveConfig() {
    const parts = repoInput.split("/");
    if (parts.length !== 2 || !config) return;
    setSaving(true);
    await api.updateRepoConfig(parts[0], parts[1], config);
    setSaving(false);
    setMessage("Config saved.");
    setTimeout(() => setMessage(""), 3000);
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-56 p-8 max-w-2xl">
        <div className="mb-8">
          <h1 className="font-mono text-2xl font-bold text-foreground">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Per-repo configuration for analysis rules
          </p>
        </div>

        {/* Repo selector */}
        <div className="flex gap-2 mb-6">
          <input
            type="text"
            value={repoInput}
            onChange={(e) => setRepoInput(e.target.value)}
            placeholder="owner/repo"
            className="flex-1 rounded-md border border-border bg-input px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <Button onClick={loadConfig} variant="outline" className="font-mono text-sm">
            Load
          </Button>
        </div>

        {config && (
          <Card className="border-border bg-card p-6 space-y-6">
            {/* CC Threshold */}
            <div>
              <label className="text-sm font-medium text-foreground block mb-2">
                Complexity Threshold
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min={1}
                  max={30}
                  value={config.cc_threshold}
                  onChange={(e) => setConfig({ ...config, cc_threshold: +e.target.value })}
                  className="flex-1 accent-primary"
                />
                <span className="font-mono text-lg font-bold text-primary w-8 text-right">
                  {config.cc_threshold}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Functions with CC above this value will be flagged for review.
              </p>
            </div>

            {/* Bandit toggle */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-foreground">Bandit Security Scan</p>
                <p className="text-xs text-muted-foreground">
                  Check for hardcoded secrets, eval() calls, etc.
                </p>
              </div>
              <Switch
                checked={config.bandit_enabled}
                onCheckedChange={(val: boolean) => setConfig({ ...config, bandit_enabled: val })}
              />
            </div>

            {/* Auto-post toggle */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-foreground">Auto-Post Reviews</p>
                <p className="text-xs text-muted-foreground">
                  Automatically post suggestions to GitHub, or queue for approval.
                </p>
              </div>
              <Switch
                checked={config.auto_post}
                onCheckedChange={(val: boolean) => setConfig({ ...config, auto_post: val })}
              />
            </div>

            {/* LLM Model */}
            <div>
              <label className="text-sm font-medium text-foreground block mb-2">
                LLM Model
              </label>
              <input
                type="text"
                value={config.llm_model}
                onChange={(e) => setConfig({ ...config, llm_model: e.target.value })}
                className="w-full rounded-md border border-border bg-input px-3 py-2 font-mono text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* Exclude Patterns */}
            <div>
              <label className="text-sm font-medium text-foreground block mb-2">
                Exclude Patterns
              </label>
              <input
                type="text"
                value={config.exclude_patterns}
                onChange={(e) => setConfig({ ...config, exclude_patterns: e.target.value })}
                placeholder="**/migrations/**, **/tests/**"
                className="w-full rounded-md border border-border bg-input px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Comma-separated glob patterns. Matching files will be skipped.
              </p>
            </div>

            {/* Save */}
            <div className="flex items-center gap-3 pt-2">
              <Button onClick={saveConfig} disabled={saving} className="font-mono">
                {saving ? "Saving..." : "Save Config"}
              </Button>
              {message && <span className="text-sm text-primary">{message}</span>}
            </div>
          </Card>
        )}
      </main>
    </div>
  );
}
```

### Step 5.12 — Add `NEXT_PUBLIC_API_URL` to frontend env

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Step 5.13 — Run the frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000`. You should see the dark dashboard with the sidebar and empty feed.

---

## Phase 6: GitHub App Setup

This phase happens in the browser, not in code.

### Step 6.1 — Register a GitHub App

1. Go to **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**.
2. Fill in:
   - **App name**: `geekPR` (or anything unique)
   - **Homepage URL**: `http://localhost:3000` (or your server URL)
   - **Webhook URL**: `https://your-domain.com/api/webhook/github` (use a tunnel like `ngrok` for local dev: `ngrok http 8000`)
   - **Webhook secret**: Generate a strong random string. Save it — you'll put it in `.env`.
3. **Permissions**:
   - **Pull requests**: Read & Write
   - **Contents**: Read-only
   - **Metadata**: Read-only
4. **Subscribe to events**: Check **Pull request**.
5. Click **Create GitHub App**.

### Step 6.2 — Generate a private key

On the app settings page, scroll to **Private keys** and click **Generate a private key**. A `.pem` file will download. Move it to a safe location (e.g., `backend/keys/geekpr.pem`). **Never commit this file.**

### Step 6.3 — Fill in `.env`

Edit `backend/.env`:

```env
GITHUB_APP_ID=123456            # From the app settings page
GITHUB_PRIVATE_KEY_PATH=./keys/geekpr.pem
GITHUB_WEBHOOK_SECRET=your-random-secret-here
```

### Step 6.4 — Install the app on a repo

1. Go to your GitHub App's public page: `https://github.com/apps/geekpr`
2. Click **Install** and select the repo(s) you want to monitor.
3. GitHub will now send webhook events to your endpoint.

### Step 6.5 — Test with ngrok (local dev)

```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) and update the webhook URL in your GitHub App settings to `https://abc123.ngrok.io/api/webhook/github`.

Now open a PR on the installed repo. Watch the Celery worker terminal — you should see the job get picked up and processed.

---

## Phase 7: Docker & Deployment

### Step 7.1 — Create `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 7.2 — Create `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

ENV NODE_ENV=production
CMD ["npm", "start"]
```

### Step 7.3 — Create `docker-compose.yml`

In the project root:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: geekpr
      POSTGRES_PASSWORD: geekpr
      POSTGRES_DB: geekpr
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    environment:
      DATABASE_URL: postgresql://geekpr:geekpr@db:5432/geekpr
      REDIS_URL: redis://redis:6379/0
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
    depends_on:
      - redis
      - db

  worker:
    build: ./backend
    command: celery -A app.tasks.celery_app worker --loglevel=info
    env_file:
      - ./backend/.env
    environment:
      DATABASE_URL: postgresql://geekpr:geekpr@db:5432/geekpr
      REDIS_URL: redis://redis:6379/0
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
    depends_on:
      - redis
      - db

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000/api

  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data

volumes:
  redis_data:
  pg_data:
  caddy_data:
```

### Step 7.4 — Create `Caddyfile`

In the project root:

```
your-domain.com {
    handle /api/* {
        reverse_proxy backend:8000
    }
    handle {
        reverse_proxy frontend:3000
    }
}
```

Replace `your-domain.com` with your actual domain. For local dev, use `localhost`.

### Step 7.5 — Launch

```bash
docker compose up --build
```

Verify:
- `http://localhost:3000` — Dashboard
- `http://localhost:8000/health` — Backend health check
- `http://localhost:8000/docs` — Swagger UI

---

## Phase 8: Testing

### Step 8.1 — Unit tests

Create `backend/tests/unit/test_complexity.py`:

```python
from app.services.complexity import analyze_complexity


def test_simple_function_not_flagged():
    code = "def add(a, b):\n    return a + b\n"
    results = analyze_complexity(code, threshold=10)
    assert len(results) == 1
    assert results[0].is_flagged is False
    assert results[0].score <= 10


def test_complex_function_flagged():
    code = """
def nightmare(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                if x > y:
                    if y > z:
                        if x > z:
                            if x + y > z:
                                if x - y < z:
                                    if x * y > z:
                                        if x / (y+1) > z:
                                            return True
    return False
"""
    results = analyze_complexity(code, threshold=5)
    assert len(results) == 1
    assert results[0].is_flagged is True
    assert results[0].score > 5
```

Create `backend/tests/unit/test_diff_analyzer.py`:

```python
from app.services.diff_analyzer import extract_changed_functions

SAMPLE_DIFF = """
diff --git a/utils.py b/utils.py
new file mode 100644
--- /dev/null
+++ b/utils.py
@@ -0,0 +1,10 @@
+def calculate_total(items):
+    total = 0
+    for item in items:
+        if item.is_active:
+            if item.discount:
+                total += item.price * (1 - item.discount)
+            else:
+                total += item.price
+    return total
+
"""


def test_extracts_new_function():
    functions = extract_changed_functions(SAMPLE_DIFF)
    assert len(functions) >= 1
    assert functions[0].function_name == "calculate_total"
    assert "calculate_total" in functions[0].source_code
```

Run:

```bash
cd backend
pytest tests/unit/ -v
```

### Step 8.2 — Integration tests

Create `backend/tests/integration/test_webhook.py`:

```python
import pytest
import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    return TestClient(app)


def sign_payload(payload: dict) -> str:
    """Generate a valid webhook signature for testing."""
    body = json.dumps(payload).encode()
    sig = hmac.new(
        settings.github_webhook_secret.encode(),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={sig}"


def test_webhook_rejects_bad_signature(client):
    response = client.post(
        "/api/webhook/github",
        json={"action": "opened"},
        headers={"X-Hub-Signature-256": "sha256=invalid"},
    )
    assert response.status_code == 401


def test_webhook_ignores_non_pr_actions(client):
    payload = {"action": "closed"}
    sig = sign_payload(payload)
    response = client.post(
        "/api/webhook/github",
        content=json.dumps(payload),
        headers={
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 200
    assert "Ignored" in response.json()["message"]
```

Run:

```bash
cd backend
pytest tests/integration/ -v
```

### Step 8.3 — Frontend tests

```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
npx playwright install
```

Add to `frontend/package.json` scripts:

```json
"test": "vitest",
"test:e2e": "playwright test"
```

### Step 8.4 — CI pipeline

Create `.github/workflows/ci.yml` in the project root:

```yaml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r backend/requirements.txt
        working-directory: .
      - run: pytest tests/ -v
        working-directory: backend

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
        working-directory: frontend
      - run: npm run build
        working-directory: frontend
```

---

## Checklist

Use this to track progress. Check off each item as you complete it.

- [ ] **Phase 1**: Folder structure, venv, dependencies, `.env.example`, `.gitignore`
- [ ] **Phase 2**: Pydantic settings, SQLAlchemy models, Alembic migrations
- [ ] **Phase 3**: Webhook verification, diff analyzer, complexity checker, Bandit scanner, LLM service, GitHub service
- [ ] **Phase 4**: Celery app, analysis task, FastAPI app + all API routes
- [ ] **Phase 5**: Next.js scaffold, theme, API client, TanStack Query, sidebar, Feed page, Analytics page, Activity page, Settings page
- [ ] **Phase 6**: GitHub App registered, private key generated, `.env` configured, app installed on a repo, tested with ngrok
- [ ] **Phase 7**: Backend Dockerfile, frontend Dockerfile, docker-compose.yml, Caddyfile, `docker compose up` works
- [ ] **Phase 8**: Unit tests pass, integration tests pass, CI pipeline runs on PRs
