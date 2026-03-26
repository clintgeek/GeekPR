import pytest
import asyncio
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.database import Base, get_db
from app.core.config import settings
from app.models.job import Job
from app.models.review import Review
from app.models.repo_config import RepoConfig
import hmac
import hashlib
import json

# Setup file-based SQLite for testing to avoid connection isolation issues
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def generate_signature(payload_bytes: bytes, secret: str) -> str:
    hash_value = hmac.new(
        secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={hash_value}"

@patch("app.api.webhook.analyze_pr_task.delay")
def test_valid_webhook_enqueues_task(mock_delay):
    # Mock task ID response
    class MockTask:
        id = "mock-task-id"
    mock_delay.return_value = MockTask()

    payload = {
        "action": "opened",
        "pull_request": {"number": 123, "title": "Test PR"},
        "repository": {"full_name": "test/repo"},
        "installation": {"id": 1}
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    signature = generate_signature(payload_bytes, settings.github_webhook_secret)

    response = client.post(
        "/api/webhook/github",
        content=payload_bytes,
        headers={"X-Hub-Signature-256": signature}
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Analysis enqueued", "task_id": "mock-task-id"}

    # Verify task was enqueued
    mock_delay.assert_called_once_with(
        installation_id=1,
        repo_full_name="test/repo",
        pr_number=123,
        pr_title="Test PR"
    )

    # Verify DB state
    db = TestingSessionLocal()
    job = db.query(Job).filter_by(celery_task_id="mock-task-id").first()
    assert job is not None
    assert job.status == "queued"
    db.close()


def test_invalid_signature_rejected():
    payload = {"action": "opened"}
    payload_bytes = json.dumps(payload).encode("utf-8")
    
    response = client.post(
        "/api/webhook/github",
        content=payload_bytes,
        headers={"X-Hub-Signature-256": "sha256=invalid"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid webhook signature"
