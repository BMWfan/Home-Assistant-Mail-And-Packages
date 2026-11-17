"""Tests for the repository-local Reflexion engine."""

import pytest

from .engine import retrieve, validate


def lesson(lesson_id="a", **overrides):
    """Build a valid lesson with optional field overrides."""
    return {
        "id": lesson_id,
        "tags": ["docker"],
        "trigger": "build failure",
        "evidence": "a" * 40,
        "action": "inspect build logs",
        "status": "approved",
        "supersedes": None,
        **overrides,
    }


def test_relevance():
    """Return lessons matching the query terms."""
    row = lesson()
    assert retrieve([row], "docker") == [row]
    assert retrieve([row], "unrelated") == []


def test_budget():
    """Respect the character budget and result limit."""
    assert retrieve([lesson()], "docker", budget=2) == []
    assert retrieve([lesson()], "docker", limit=0) == []


def test_invalid_budget():
    """Reject bounds that cannot describe a valid result."""
    for budget in (-1, 0, 1):
        with pytest.raises(ValueError):
            retrieve([], "docker", budget=budget)
    with pytest.raises(ValueError):
        retrieve([], "docker", limit=-1)


def test_credential_screen():
    """Reject synthetic strings that resemble credentials."""
    for action in (
        "token=" + "x" * 24,
        "-----BEGIN PRIVATE KEY-----",
        "ghp_" + "x" * 30,
    ):
        with pytest.raises(ValueError, match="Potential credential"):
            validate([lesson(action=action)])


def test_candidate():
    """Omit candidate lessons from retrieval."""
    assert retrieve([lesson(status="candidate")], "docker") == []


def test_supersession():
    """Omit lessons replaced by an approved lesson."""
    original = lesson()
    replacement = lesson("b", action="inspect failed build step", supersedes="a")
    assert retrieve([original, replacement], "docker") == [replacement]


def test_duplicate():
    """Reject duplicate lessons after normalization."""
    with pytest.raises(ValueError):
        validate([lesson(), lesson("b", action="Inspect build logs!")])


def test_malformed():
    """Reject rows with missing fields."""
    with pytest.raises(ValueError):
        validate([{}])


def test_order():
    """Break relevance ties by lesson ID."""
    first = lesson()
    second = lesson("b", action="verify build output")
    assert retrieve([second, first], "docker") == [first, second]
