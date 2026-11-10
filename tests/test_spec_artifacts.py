"""Tests for the deterministic specification artifact quality gate."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from check_spec_artifacts import changed_paths, check_spec_artifacts


def _write_bundle(root: Path, headings: tuple[str, ...] | None = None) -> None:
    specs = root / "specs"
    specs.mkdir()
    spec_headings = headings or (
        "## Goal",
        "## Requirements",
        "## Acceptance criteria",
        "## Design",
        "## Plan",
        "## Tasks",
    )
    (specs / "001-example.md").write_text("\n".join(spec_headings), encoding="utf-8")
    (specs / "001-verification.md").write_text(
        "## Test status matrix\n## Next actions\n", encoding="utf-8"
    )


class TestSpecArtifactCheck(unittest.TestCase):
    """Validate pass, actionable failures, and grandfathered legacy specs."""

    def test_changed_spec_with_required_artifacts_passes(self) -> None:
        """A changed spec passes when its required sections and companion exist."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_bundle(root)

            assert check_spec_artifacts(["specs/001-example.md"], root) == []

    def test_changed_spec_reports_missing_companion_and_sections(self) -> None:
        """A malformed changed spec reports its missing artifacts and sections."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            specs = root / "specs"
            specs.mkdir()
            (specs / "001-example.md").write_text("## Goal\n", encoding="utf-8")

            errors = check_spec_artifacts(["specs/001-example.md"], root)

            assert any(
                "required verification artifact is missing" in error for error in errors
            )
            assert any("## Requirements" in error for error in errors)
            assert any("## Tasks" in error for error in errors)

    def test_deleting_verification_companion_fails(self) -> None:
        """Deleting a companion alone is still checked as a changed spec."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            specs = root / "specs"
            specs.mkdir()
            (specs / "001-example.md").write_text(
                "## Goal\n## Requirements\n## Acceptance criteria\n## Design\n## Plan\n## Tasks",
                encoding="utf-8",
            )

            with patch("check_spec_artifacts.subprocess.run") as run:
                run.return_value.stdout = "specs/001-verification.md\n"
                changed = changed_paths("a" * 40)

            errors = check_spec_artifacts(changed, root)

            assert "--diff-filter=ACMRD" in run.call_args.args[0]
            assert any(
                "required verification artifact is missing" in error for error in errors
            )

    def test_unchanged_legacy_spec_is_grandfathered(self) -> None:
        """An untouched legacy spec is not subjected to the new artifact gate."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            specs = root / "specs"
            specs.mkdir()
            (specs / "001-legacy.md").write_text("legacy", encoding="utf-8")

            assert check_spec_artifacts([], root) == []


class TestFolderSpecArtifacts(unittest.TestCase):
    """Cover folder conventions without weakening legacy or deletion checks."""

    def setUp(self) -> None:
        """Create an independent specification fixture."""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.folder = self.root / "specs/009-example"
        self.folder.mkdir(parents=True)
        for name in ("spec.md", "tasks.md"):
            (self.folder / name).write_text("# Test artifact\n", encoding="utf-8")

    def test_minimum_medium_bundle_passes(self) -> None:
        """A bounded feature needs spec/tasks, without a compulsory large plan."""
        assert check_spec_artifacts(["specs/009-example/spec.md"], self.root) == []

    def test_complete_large_bundle_passes(self) -> None:
        """A full planning/verification pair is valid."""
        for name in ("plan.md", "verification.md"):
            (self.folder / name).write_text("# Evidence\n", encoding="utf-8")
        assert check_spec_artifacts(["specs/009-example/plan.md"], self.root) == []

    def test_missing_tasks_fails(self) -> None:
        """Removing the task artifact cannot bypass validation."""
        (self.folder / "tasks.md").unlink()
        errors = check_spec_artifacts(["specs/009-example/tasks.md"], self.root)
        assert any("tasks.md" in error for error in errors)

    def test_deleted_verification_fails(self) -> None:
        """A remaining plan requires its deleted evidence companion."""
        (self.folder / "plan.md").write_text("# Plan\n", encoding="utf-8")
        errors = check_spec_artifacts(["specs/009-example/verification.md"], self.root)
        assert any("verification.md" in error for error in errors)

    def test_deleting_both_large_artifacts_fails(self) -> None:
        """Deleting both companions must not erase evidence without a failure."""
        errors = check_spec_artifacts(
            ["specs/009-example/plan.md", "specs/009-example/verification.md"],
            self.root,
        )
        assert len(errors) == 2

    def test_empty_artifact_fails(self) -> None:
        """An empty file is not sufficient documentation."""
        (self.folder / "tasks.md").write_text("", encoding="utf-8")
        assert check_spec_artifacts(["specs/009-example/spec.md"], self.root)

    def test_duplicate_legacy_number_fails(self) -> None:
        """Folder adoption must not reuse an active legacy SPEC identifier."""
        (self.root / "specs/009-existing.md").write_text("legacy", encoding="utf-8")
        errors = check_spec_artifacts(["specs/009-example/spec.md"], self.root)
        assert any("already used" in error for error in errors)

    def test_untouched_legacy_remains_grandfathered(self) -> None:
        """Adding a new folder does not retroactively gate an unrelated old spec."""
        (self.root / "specs/001-legacy.md").write_text("legacy", encoding="utf-8")
        assert check_spec_artifacts(["specs/009-example/tasks.md"], self.root) == []


if __name__ == "__main__":
    unittest.main()
