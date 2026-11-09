"""Mocked maintenance coverage, independent of integration/production fixtures."""

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

PATH = Path(__file__).parents[1] / ".github/actions/maintenance-monitor/monitor.py"
spec = importlib.util.spec_from_file_location("monitor", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def configuration(*sources):
    return {"version": 1, "mode": "report", "sources": list(sources)}


def release(repository="home-assistant/core", identifier="core"):
    return {"id": identifier, "kind": "release", "repository": repository}


def payload(version="2026.11.0"):
    return json.dumps(
        [
            {
                "id": 1,
                "tag_name": version,
                "name": version,
                "html_url": "https://github.com/home-assistant/core/releases/tag/"
                + version,
                "published_at": "2026-11-04T00:00:00Z",
                "draft": False,
                "prerelease": False,
            }
        ]
    ).encode()


class MonitorTests(unittest.TestCase):
    def test_nonfork_baseline_and_dedup(self):
        config = configuration(release())
        first, state = m.build_report(config, None, lambda url: payload(), "now")
        second, next_state = m.build_report(
            config, state, lambda url: payload(), "later"
        )
        self.assertTrue(first["success"])
        self.assertEqual(len(first["findings"]), 1)
        self.assertFalse(second["findings"])
        self.assertEqual(next_state["sources"]["core"]["last_success"], "later")
        self.assertEqual(first["issue_creation"], "disabled")
        self.assertEqual(first["delegation"], "disabled")

    def test_changed_release_is_observed(self):
        config = configuration(release())
        _, state = m.build_report(config, None, lambda url: payload("2026.10.4"))
        report, _ = m.build_report(config, state, lambda url: payload())
        self.assertEqual(report["findings"][0]["version"], "2026.11.0")
        self.assertEqual(report["findings"][0]["risk"], "unknown_until_reviewed")

    def test_fork_requires_explicit_upstream_and_records_sha(self):
        source = {
            "id": "upstream",
            "kind": "upstream",
            "repository": "example/upstream",
            "ref": "main",
        }
        commit = [
            {
                "sha": "a" * 40,
                "html_url": "https://github.com/example/upstream/commit/" + "a" * 40,
                "commit": {"message": "Change\nDetails", "committer": {"date": "now"}},
            }
        ]
        report, _ = m.build_report(
            configuration(source), None, lambda url: json.dumps(commit).encode()
        )
        self.assertEqual(report["findings"][0]["version"], "a" * 40)
        source.pop("ref")
        with self.assertRaises(ValueError):
            m.validate(configuration(source))

    def test_prerelease_is_skipped(self):
        records = json.loads(payload())
        preview = {**records[0], "id": 2, "tag_name": "2027.1.0b1", "prerelease": True}
        result = m.snapshot(
            release(), lambda url: json.dumps([preview, *records]).encode()
        )
        self.assertEqual(result[0]["version"], "2026.11.0")

    def test_failure_does_not_advance_any_review_state(self):
        sources = configuration(
            release(), release("home-assistant/frontend", "frontend")
        )

        def fetch(url):
            if "frontend" in url:
                raise m.SourceError("http_503")
            return payload()

        report, state = m.build_report(sources, None, fetch)
        self.assertFalse(report["success"])
        self.assertIsNone(state)
        self.assertEqual(report["errors"], [{"source": "frontend", "code": "http_503"}])
        self.assertIn("not advanced", m.markdown(report))

    def test_malformed_response_fails_without_raw_data(self):
        report, state = m.build_report(
            configuration(release()), None, lambda url: b'{"token":"private"}'
        )
        self.assertIsNone(state)
        self.assertNotIn("private", json.dumps(report))

    def test_config_identity_change_resets_only_that_source(self):
        _, state = m.build_report(configuration(release()), None, lambda url: payload())
        changed = release("home-assistant/frontend")
        report, _ = m.build_report(configuration(changed), state, lambda url: payload())
        self.assertEqual(len(report["findings"]), 1)

    def test_mutation_and_arbitrary_urls_are_rejected_before_fetch(self):
        for override in [
            {"mode": "issues"},
            {"delegate": True},
            {"create_issues": True},
            {
                "sources": [
                    {"id": "x", "kind": "feed", "url": "https://internal.invalid"}
                ]
            },
        ]:
            fetch = unittest.mock.Mock()
            with self.assertRaises(ValueError):
                m.build_report({**configuration(release()), **override}, None, fetch)
            fetch.assert_not_called()

    def test_official_atom_feed(self):
        source = {
            "id": "ha-news",
            "kind": "feed",
            "url": "https://contributors.home-assistant.io/blog/rss.xml",
        }
        data = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>API deprecation</title><id>entry-1</id><updated>now</updated><link rel="alternate" href="https://developers.home-assistant.io/blog/2026/11/01/change"/></entry></feed>'
        report, _ = m.build_report(configuration(source), None, lambda url: data)
        self.assertEqual(report["findings"][0]["title"], "API deprecation")
        self.assertEqual(report["findings"][0]["revision"], "now")

    def test_advisory_is_not_claimed_as_installed_exposure(self):
        source = {
            "id": "aiohttp",
            "kind": "advisory",
            "ecosystem": "pip",
            "package": "aiohttp",
        }
        data = [
            {
                "ghsa_id": "GHSA-example",
                "summary": "Review advisory",
                "html_url": "https://github.com/advisories/GHSA-example",
                "updated_at": "now",
            }
        ]
        report, _ = m.build_report(
            configuration(source), None, lambda url: json.dumps(data).encode()
        )
        self.assertIn("unconfirmed", report["findings"][0]["applicability"])
        self.assertEqual(report["findings"][0]["priority"], "high")

    def test_credential_citation_and_redirect_are_rejected(self):
        for url in [
            "https://user:password@github.com/a",
            "http://github.com/a",
            "https://github.com/a?token=x",
            "https://private.invalid/a",
        ]:
            with self.assertRaises(m.SourceError):
                m.public_link(url)
        with self.assertRaises(m.SourceError):
            m.NoRedirect().redirect_request(
                None, None, 302, "", {}, "https://other.invalid"
            )

    def test_retry_is_bounded_and_respects_retry_after(self):

        error = HTTPError(
            "https://api.github.com/x", 429, "", {"Retry-After": "31"}, None
        )
        opener = unittest.mock.Mock()
        opener.open.side_effect = error
        with (
            patch.object(m, "build_opener", return_value=opener),
            patch.object(m.time, "sleep") as sleep,
        ):
            with self.assertRaises(m.SourceError):
                m.download("https://api.github.com/x")
            sleep.assert_not_called()
            self.assertEqual(opener.open.call_count, 1)

    def test_markdown_does_not_render_raw_html(self):
        data = json.loads(payload())
        data[0]["name"] = "<script>alert(1)</script>|extra"
        report, _ = m.build_report(
            configuration(release()), None, lambda url: json.dumps(data).encode()
        )
        # Titles remain data in JSON, but raw source HTML is never interpolated in markdown.
        self.assertNotIn("<script>", m.markdown(report))
