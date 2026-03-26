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
