"""
LLM client — structured refactor suggestions via aiGeek.

Default target is aiGeek (baseGeek's OpenAI-compatible proxy). Because
aiGeek accepts `response_format: {type: "json_schema", ...}` and maps it
to native tool-use on Anthropic + responseSchema on Gemini, Instructor's
Pydantic-validated round-trips work end-to-end without any additional
prompt engineering on geekPR's side.

`openai` and `ollama` paths are retained as direct-access fallbacks for
local testing or cases where a specific provider is needed without
going through aiGeek.
"""

import instructor
from openai import OpenAI

from app.core.config import settings
from app.schemas.llm import RefactorSuggestion


# Language → code-fence tag + reviewer persona hint. Used to shape the
# prompt so the LLM gets the right syntactic cues for idiomatic
# suggestions.
_LANGUAGE_HINTS: dict[str, tuple[str, str]] = {
    "python": ("python", "Pythonic idioms, PEP 8, type hints, Google-style docstrings"),
    "javascript": ("javascript", "modern ES2020+ idioms, functional composition where natural, JSDoc for public functions"),
    "rust": ("rust", "idiomatic Rust: ownership-aware, Result/Option over exceptions, rustdoc comments"),
    "go": ("go", "idiomatic Go: early returns, small interfaces, GoDoc comments, explicit error handling"),
}


def get_llm_client(
    provider: str | None = None,
    model: str | None = None,
) -> tuple[instructor.Instructor, str]:
    """
    Create an Instructor-patched OpenAI client for the chosen provider.

    Args:
        provider: "aigeek" (default), "openai", or "ollama". Falls back to
            settings.default_llm_provider.
        model: Model name override. For aigeek, can be "<provider>/<model>"
            to pin a specific backend (e.g. "anthropic/claude-sonnet-4-6").

    Returns:
        (Instructor client, resolved model name).
    """
    provider = provider or settings.default_llm_provider

    if provider == "aigeek":
        if not settings.aigeek_api_key:
            raise RuntimeError(
                "aigeek_api_key is empty — set AIGEEK_API_KEY in .env "
                "(bg_<64-hex>) or switch default_llm_provider."
            )
        client = OpenAI(
            api_key=settings.aigeek_api_key,
            base_url=settings.aigeek_base_url,
        )
        resolved_model = model or settings.aigeek_default_model
    elif provider == "openai":
        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        resolved_model = model or settings.openai_model
    elif provider == "ollama":
        client = OpenAI(
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",
        )
        resolved_model = model or settings.ollama_model
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    return instructor.from_openai(client), resolved_model


def request_refactor(
    function_source: str,
    complexity_score: int,
    function_name: str,
    language: str = "python",
    provider: str | None = None,
    model: str | None = None,
) -> RefactorSuggestion:
    """
    Ask the LLM to suggest a refactor for a complex function.

    Args:
        function_source: Full source of the function.
        complexity_score: Cyclomatic complexity (or analyzer-specific score).
        function_name: Name of the function.
        language: Canonical language name from the analyzer ("python",
            "javascript", "rust", "go"). Shapes the prompt and code fence.
        provider: "aigeek" (default), "openai", or "ollama".
        model: Model name or provider/model pin.

    Returns:
        A RefactorSuggestion validated against the Pydantic schema.
    """
    client, resolved_model = get_llm_client(provider=provider, model=model)

    fence, _ = _LANGUAGE_HINTS.get(language, (language, ""))

    prompt = f"""You are the on-call engineer triaging a pull request at 2am.
Your job is to flag things that would wake you up, NOT to improve readability.

Return severity=NONE for anything that is only a style / complexity / SRP
concern. Complex code is not a bug. Deep nesting is not a bug. A function
being hard to read is not a bug. Save the severity levels for actual
production risk.

Flag severity=HIGH or severity=CRITICAL only if one of these is true:
  - Security: injection (SQL, command, path), auth bypass, hardcoded
    secret, unsanitized user input, broken crypto, TLS misuse.
  - Crash: unhandled exception on realistic input, null/None deref,
    unbounded recursion, resource leak (file/socket/lock never freed).
  - Data loss: silent write failure, missing transaction boundary,
    off-by-one that drops records, race that overwrites good data.
  - Concurrency: TOCTOU, missing lock, shared-mutable-state bug, deadlock.
  - Correctness: logic inverted, wrong branch, incorrect API usage that
    will misbehave in production (not just "looks fragile").

If you are unsure whether something is a real bug or just ugly code:
severity=NONE. We would rather miss a subtle bug than fire twenty
false alarms at a busy engineer.

The complexity score ({complexity_score}) is just what surfaced this
function for review. It is NOT itself a reason to flag.

The {language} function `{function_name}`:

```{fence}
{function_source}
```
"""

    return client.chat.completions.create(
        model=resolved_model,
        response_model=RefactorSuggestion,
        messages=[{"role": "user", "content": prompt}],
        # Refactor suggestions include a full rewritten function plus
        # explanation; 1000 tokens (aiGeek's default) truncates mid-reply
        # and instructor rejects the incomplete tool_call.
        max_tokens=4096,
        max_retries=2,
    )
