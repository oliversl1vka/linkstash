from pathlib import Path
import re


ALLOWED_BRAIN_REPO_PATHS = {
    "Claude-Code",
    "Entries",
    "Home.md",
    "Logs",
    "Topics",
    "index.md",
}


def sanitize_git_error_message(error: object) -> str:
    """Redact credentials from git/HTTP error messages before logging or returning them."""
    message = str(error)
    message = re.sub(r"(x-access-token:)[^@/\s]+@", r"\1***@", message)
    message = re.sub(r"(https?://[^:/@\s]+:)[^@/\s]+@", r"\1***@", message)
    return message


def sanitize_brain_repo_contents(brain_dir: Path) -> list[str]:
    """Remove files outside the dedicated brain/artifact allowlist and return removed top-level paths."""
    removed_paths: list[str] = []
    if not brain_dir.exists():
        return removed_paths

    for child in brain_dir.iterdir():
        if child.name == ".git" or child.name in ALLOWED_BRAIN_REPO_PATHS:
            continue
        if child.is_symlink() or not child.is_dir():
            child.unlink()
        else:
            for nested in sorted(child.rglob("*"), reverse=True):
                if nested.is_symlink() or nested.is_file():
                    nested.unlink()
                elif nested.is_dir():
                    nested.rmdir()
            child.rmdir()
        removed_paths.append(child.name)

    return removed_paths
