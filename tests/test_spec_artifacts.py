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
                "\n".join(
                    (
                        "## Goal",
                        "## Requirements",
                        "## Acceptance criteria",
                        "## Design",
                        "## Plan",
                        "## Tasks",
                    )
                ),
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


if __name__ == "__main__":
    unittest.main()
