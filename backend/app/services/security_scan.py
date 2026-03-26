import json
import subprocess
import tempfile
from dataclasses import dataclass


@dataclass
class SecurityIssue:
    """A security issue found by Bandit."""
    test_id: str
    description: str
    severity: str
    confidence: str
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
