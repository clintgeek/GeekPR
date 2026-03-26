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
    allow_origins=["*"],
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
