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
