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
