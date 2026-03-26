import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.database import Base, get_db
from app.models.review import Review
from app.models.job import Job
from app.models.repo_config import RepoConfig

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


def test_list_reviews_empty():
    response = client.get("/api/reviews/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["reviews"] == []


def test_list_reviews_with_data():
    db = TestingSessionLocal()
    review = Review(
        repo_full_name="test/repo",
        pr_number=1,
        pr_title="Fix bug",
        function_name="add",
        file_path="main.py",
        complexity_score=5,
        priority="Low",
        status="pending"
    )
    db.add(review)
    db.commit()
    db.close()

    response = client.get("/api/reviews/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["reviews"][0]["repo"] == "test/repo"
    assert data["reviews"][0]["pr_number"] == 1


def test_get_single_review():
    db = TestingSessionLocal()
    review = Review(
        repo_full_name="test/repo2",
        pr_number=2,
        pr_title="New feature",
    )
    db.add(review)
    db.commit()
    review_id = review.id
    db.close()

    response = client.get(f"/api/reviews/{review_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["repo"] == "test/repo2"
    assert data["pr_number"] == 2


def test_get_review_not_found():
    response = client.get("/api/reviews/999")
    assert response.status_code == 404
