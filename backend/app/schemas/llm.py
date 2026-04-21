from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """How much you'd care about this finding at 2am on a busy Tuesday.

    CRITICAL — data loss, security breach, guaranteed production crash.
    HIGH     — likely to break on real inputs; fix before next release.
    MEDIUM   — legitimate correctness concern but not urgent.
    NONE     — code is complex but not actually broken; don't post.
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    NONE = "none"


class IssueType(str, Enum):
    SECURITY = "security"            # SQLi / XSS / command-injection / auth / secrets
    CRASH = "crash"                  # unhandled exception, null deref, resource leak
    DATA_LOSS = "data_loss"          # silent corruption, missing error handling on writes
    CONCURRENCY = "concurrency"      # race condition, missing lock, TOCTOU
    CORRECTNESS = "correctness"      # logic bug, off-by-one, wrong API usage
    NONE = "none"                    # no real issue — paired with Severity.NONE


class RefactorSuggestion(BaseModel):
    """Triage output from the reviewer.

    Only Severity.CRITICAL and Severity.HIGH are posted to the PR; everything
    else is treated as noise and dropped. The LLM should prefer Severity.NONE
    when the only objection is readability, style, or complexity-for-its-own-
    sake.
    """
    severity: Severity = Field(
        description=(
            "How serious this is in production terms. Use NONE for pure "
            "style/readability concerns — those never wake anyone up."
        )
    )
    issue_type: IssueType = Field(
        description="Category of production risk. Use NONE when severity is NONE."
    )
    summary: str = Field(
        description=(
            "One sentence describing the SPECIFIC risk — what goes wrong, "
            "under what input. Not 'this is hard to read.'"
        )
    )
    suggested_fix: str | None = Field(
        default=None,
        description=(
            "Minimal code change that addresses the risk. Only required for "
            "CRITICAL / HIGH severity; may be None otherwise."
        ),
    )
    explanation: str = Field(
        description="Why this is the production risk you claimed it is."
    )
