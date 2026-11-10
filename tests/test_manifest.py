"""Tests for the Home Assistant integration manifest contract."""

import json
from pathlib import Path


def test_integration_manifest_contract() -> None:
    """Keep the required Home Assistant manifest metadata present and valid."""
    manifest_path = (
        Path(__file__).parents[1]
        / "custom_components"
        / "mail_and_packages"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert {
        "domain",
        "name",
        "config_flow",
        "documentation",
        "issue_tracker",
        "requirements",
        "version",
    } <= manifest.keys()
    assert manifest["domain"] == "mail_and_packages"
    assert manifest["name"] == "Mail and Packages"
    assert manifest["config_flow"] is True
    assert all(isinstance(requirement, str) for requirement in manifest["requirements"])
    assert manifest["version"]
