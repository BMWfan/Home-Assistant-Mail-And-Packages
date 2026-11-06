"""Validate changed specification artifacts using the repository's SDD layout."""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
from pathlib import Path

SPEC_PATH = re.compile(r"^specs/(?P<number>\d{3})-(?P<slug>[a-z0-9][a-z0-9-]*)\.md$")
SPEC_HEADINGS = (
    "## Goal",
    "## Requirements",
    "## Acceptance criteria",
    "## Design",
    "## Plan",
    "## Tasks",
)
VERIFICATION_HEADINGS = ("## Test status matrix", "## Next actions")
LOGGER = logging.getLogger(__name__)


def changed_paths(base_sha: str) -> list[str]:
    """Return added, copied, modified, and renamed paths since the PR base."""
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", base_sha):
        raise ValueError("base SHA must be a 40- or 64-character hexadecimal commit")
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMR",
            f"{base_sha}...HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def check_spec_artifacts(changed: list[str], repository_root: Path) -> list[str]:
    """Check only changed root-level specs and their required companion artifacts."""
    candidates = [
        path for path in changed if path.startswith("specs/") and path.endswith(".md")
    ]
    if not candidates:
        return []

    errors: list[str] = []
    numbers: set[str] = set()
    for path in candidates:
        match = SPEC_PATH.fullmatch(path)
        if match is None:
            errors.append(
                f"{path}: use the existing specs/NNN-name.md or "
                "specs/NNN-verification.md layout."
            )
            continue
        numbers.add(match.group("number"))

    for number in sorted(numbers):
        spec_files = sorted(
            path
            for path in (repository_root / "specs").glob(f"{number}-*.md")
            if path.name != f"{number}-verification.md"
        )
        if len(spec_files) != 1:
            errors.append(
                f"specs/{number}-*.md: expected exactly one specification document "
                f"for changed spec {number}; found {len(spec_files)}."
            )
            continue

        spec_path = spec_files[0]
        verification_path = repository_root / "specs" / f"{number}-verification.md"
        errors.extend(_missing_headings(spec_path, SPEC_HEADINGS))
        if not verification_path.is_file():
            errors.append(
                f"{verification_path.relative_to(repository_root)}: required verification "
                "artifact is missing."
            )
        else:
            errors.extend(_missing_headings(verification_path, VERIFICATION_HEADINGS))
    return errors


def _missing_headings(path: Path, required: tuple[str, ...]) -> list[str]:
    headings = {
        line.strip().casefold()
        for line in path.read_text(encoding="utf-8").splitlines()
    }
    return [
        f"{path}: add the required `{heading}` section."
        for heading in required
        if heading.casefold() not in headings
    ]


def main() -> int:
    """Run the changed-spec artifact check for a pull request."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", required=True, help="PR base commit SHA")
    args = parser.parse_args()

    try:
        changed = changed_paths(args.base_ref)
    except (OSError, subprocess.CalledProcessError, ValueError) as err:
        LOGGER.error("Could not determine changed files: %s", err)
        return 2

    errors = check_spec_artifacts(changed, Path.cwd())
    if errors:
        LOGGER.error("Specification artifact validation failed:")
        for error in errors:
            LOGGER.error("- %s", error)
        return 1
    if any(path.startswith("specs/") and path.endswith(".md") for path in changed):
        LOGGER.info(
            "Changed specification artifacts satisfy the repository SDD structure."
        )
    else:
        LOGGER.info("No changed spec artifacts; existing specs are grandfathered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
