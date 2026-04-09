from src.bot import _count_pending_brain_changes


def test_count_pending_brain_changes_counts_main_claude_artifacts_only():
    status_lines = [
        "?? Entries/2026-04-09-entry-one.md",
        "?? Entries/2026-04-09-entry-two.md",
        "?? Claude-Code/index.md",
        "?? Claude-Code/skills/dev/testing/browser-regression-testing/SKILL.md",
        "?? Claude-Code/skills/dev/testing/browser-regression-testing/references/playwright-notes.md",
        "?? Claude-Code/instructions/dev/mintlify-adoption.md",
        "?? Claude-Code/prompts/dev/release-prompt.md",
        "?? Claude-Code/prompts/dev/release-prompt_references/example.md",
    ]

    new_entries, claude_artifacts = _count_pending_brain_changes(status_lines)

    assert new_entries == 2
    assert claude_artifacts == 3


def test_count_pending_brain_changes_handles_renamed_paths():
    status_lines = [
        "R  Claude-Code/instructions/dev/old-name.md -> Claude-Code/instructions/dev/new-name.md",
        "R  Entries/2026-04-08-old.md -> Entries/2026-04-09-new.md",
    ]

    new_entries, claude_artifacts = _count_pending_brain_changes(status_lines)

    assert new_entries == 1
    assert claude_artifacts == 1