"""Read-only, source-cited maintenance snapshots for fork and non-fork projects."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree.ElementTree import ParseError

import yaml
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

VERSION = 1
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ALLOWED_FEEDS = {
    "https://contributors.home-assistant.io/blog/rss.xml",
    "https://www.python.org/downloads/feed.rss",
}


class NoRedirect(HTTPRedirectHandler):
    """Never forward API credentials to redirect destinations."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: PLR0917 - urllib override signature
        """Reject redirects before issuing another request."""
        raise SourceError("unexpected_redirect")


class SourceError(Exception):
    """A source failed; its previous review state must not advance."""


def download(url, token=""):
    """Fetch bounded public data; never disclose response bodies or credentials."""
    headers = {
        "User-Agent": "SDD-Light-Maintenance/1",
        "Accept": "application/vnd.github+json",
    }
    if token and urlparse(url).hostname == "api.github.com":
        headers["Authorization"] = "Bearer " + token
    for attempt in range(3):
        try:
            with build_opener(NoRedirect).open(
                Request(url, headers=headers), timeout=20
            ) as response:
                # All configured API/feed endpoints are direct public endpoints.
                if urlparse(response.url).hostname != urlparse(url).hostname:
                    raise SourceError("unexpected_redirect")
                data = response.read(2_000_001)
                if len(data) > 2_000_000:
                    raise SourceError("response_too_large")
                return data
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise SourceError(f"http_{error.code}") from None
            delay = error.headers.get("Retry-After", "")
            if delay.isdigit() and int(delay) > 30:
                raise SourceError("rate_limited_retry_later") from None
            time.sleep(int(delay) if delay.isdigit() else 2**attempt)
        except (URLError, TimeoutError, OSError):
            if attempt == 2:
                raise SourceError("network_unavailable") from None
            time.sleep(2**attempt)
    raise SourceError("network_unavailable")


def validate(config):
    """Reject unsupported or mutating configurations before any network request."""
    if not isinstance(config, dict) or config.get("version") != VERSION:
        raise ValueError("configuration_version")
    if (
        config.get("mode") != "report"
        or config.get("create_issues", False)
        or config.get("delegate", False)
    ):
        raise ValueError("only_read_only_report_mode_supported")
    sources = config.get("sources")
    if not isinstance(sources, list) or not sources or len(sources) > 30:
        raise ValueError("sources_required_maximum_30")
    ids = set()
    for source in sources:
        if not isinstance(source, dict) or not re.fullmatch(
            r"[a-z0-9_-]{1,60}", source.get("id", "")
        ):
            raise ValueError("invalid_source_id")
        if source["id"] in ids:
            raise ValueError("duplicate_source_id")
        ids.add(source["id"])
        validate_source(source)
    return config


def validate_source(source):
    """Validate one adapter configuration."""
    kind = source.get("kind")
    if kind in ("release", "upstream"):
        if not REPOSITORY.fullmatch(source.get("repository", "")):
            raise ValueError("invalid_repository")
        if kind == "upstream" and not re.fullmatch(
            r"[A-Za-z0-9_./-]{1,200}", source.get("ref", "")
        ):
            raise ValueError("explicit_upstream_ref_required")
    elif kind == "feed":
        if source.get("url") not in ALLOWED_FEEDS:
            raise ValueError("unapproved_official_feed")
    elif kind == "advisory":
        if source.get("ecosystem") not in ("pip", "npm") or not re.fullmatch(
            r"[@A-Za-z0-9_./-]{1,100}", source.get("package", "")
        ):
            raise ValueError("invalid_advisory_package")
    else:
        raise ValueError("unsupported_source_kind")


def public_link(value):
    """Only emit safe, credential-free HTTPS citations."""
    value = str(value or "")
    url = urlparse(value)
    if (
        url.scheme != "https"
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise SourceError("invalid_citation")
    if url.hostname not in {
        "github.com",
        "developers.home-assistant.io",
        "contributors.home-assistant.io",
        "www.home-assistant.io",
        "www.python.org",
        "docs.python.org",
    }:
        raise SourceError("unapproved_citation_host")
    return value


def snapshot(source, fetch):
    """Read one configured adapter without inventing an upstream relationship."""
    kind = source["kind"]
    if kind == "release":
        url = (
            f"https://api.github.com/repos/{source['repository']}/releases?per_page=20"
        )
        releases = json.loads(fetch(url))
        if not isinstance(releases, list):
            raise SourceError("invalid_releases")
        stable = next(
            (r for r in releases if not r.get("draft") and not r.get("prerelease")),
            None,
        )
        if stable is None:
            raise SourceError("no_stable_release_found")
        return [
            {
                "version": stable["tag_name"],
                "title": stable.get("name") or stable["tag_name"],
                "url": stable["html_url"],
                "published_at": stable.get("published_at"),
                "revision": str(stable["id"]),
            }
        ]
    if kind == "upstream":
        url = (
            f"https://api.github.com/repos/{source['repository']}/commits?"
            + urlencode({"sha": source["ref"], "per_page": 1})
        )
        commits = json.loads(fetch(url))
        commit = commits[0]
        return [
            {
                "version": commit["sha"],
                "title": commit["commit"]["message"].splitlines()[0],
                "url": commit["html_url"],
                "published_at": commit["commit"]["committer"]["date"],
                "revision": commit["sha"],
            }
        ]
    if kind == "advisory":
        url = "https://api.github.com/advisories?" + urlencode(
            {
                "ecosystem": source["ecosystem"],
                "affects": source["package"],
                "per_page": 20,
            }
        )
        advisories = json.loads(fetch(url))
        if not isinstance(advisories, list):
            raise SourceError("invalid_advisories")
        return [
            {
                "version": a["ghsa_id"],
                "title": a["summary"],
                "url": a["html_url"],
                "published_at": a.get("published_at"),
                "revision": a["updated_at"],
            }
            for a in advisories
        ]
    return feed_snapshot(source, fetch)


def feed_value(entry, name):
    """Read an Atom or RSS field without external entities."""
    return (
        entry.findtext("{http://www.w3.org/2005/Atom}" + name)
        or entry.findtext(name)
        or ""
    )


def feed_snapshot(source, fetch):
    """Parse bounded official Atom/RSS entries using a hardened parser."""
    tree = ET.fromstring(fetch(source["url"]))
    entries = tree.findall("{http://www.w3.org/2005/Atom}entry") or tree.findall(
        "./channel/item"
    )
    if not entries:
        raise SourceError("empty_feed")
    items = []
    for entry in entries[:20]:
        link = feed_value(entry, "link")
        for element in entry.findall("{http://www.w3.org/2005/Atom}link"):
            if element.get("rel", "alternate") == "alternate":
                link = element.get("href", "")
                break
        title = feed_value(entry, "title")
        if source["url"].startswith("https://www.python.org") and re.search(
            r"alpha|beta|candidate|\drc\d|\db\d|\da\d", title, re.IGNORECASE
        ):
            continue
        items.append(
            {
                "version": feed_value(entry, "id") or feed_value(entry, "guid") or link,
                "title": title,
                "url": link,
                "published_at": feed_value(entry, "updated")
                or feed_value(entry, "pubDate"),
                "revision": feed_value(entry, "updated")
                or feed_value(entry, "guid")
                or link,
            }
        )
    return items


def build_report(config, previous, fetch, now=None):
    """Deduplicate observations; advance state only if every source succeeds."""
    validate(config)
    if previous and previous.get("version") != VERSION:
        raise ValueError("state_version")
    previous = previous or {"version": VERSION, "sources": {}}
    observed = now or datetime.now(UTC).isoformat()
    report = {
        "version": VERSION,
        "mode": "report",
        "observed_at": observed,
        "project": config.get("project", ""),
        "project_sha": os.environ.get("GITHUB_SHA", "unknown_local_checkout"),
        "human_review": "not_recorded",
        "sources": [],
        "findings": [],
        "errors": [],
        "delegation": "disabled",
        "issue_creation": "disabled",
    }
    state = {"version": VERSION, "sources": {}}
    for source in config["sources"]:
        identity = hashlib.sha256(
            json.dumps(source, sort_keys=True).encode()
        ).hexdigest()
        old = previous.get("sources", {}).get(source["id"], {})
        seen = set(old.get("seen", [])) if old.get("identity") == identity else set()
        try:
            records = snapshot(source, fetch)
            fingerprints = set()
            for record in records:
                record["url"] = public_link(record["url"])
                fingerprint = hashlib.sha256(
                    json.dumps(record, sort_keys=True).encode()
                ).hexdigest()
                fingerprints.add(fingerprint)
                if fingerprint not in seen:
                    report["findings"].append(
                        {
                            **record,
                            "source": source["id"],
                            "fingerprint": fingerprint,
                            "decision": "defer",
                            "priority": "high"
                            if source["kind"] == "advisory"
                            else "normal",
                            "relevance": source.get(
                                "relevance", "Requires project-specific review"
                            ),
                            "benefit": "Assess supported platform/dependency compatibility",
                            "risk": "unknown_until_reviewed",
                            "effort": "unknown",
                            "recommendation": "Review the cited change against project contracts; add focused regressions before adoption.",
                            "applicability": "unconfirmed; advisory package match does not establish installed-version exposure"
                            if source["kind"] == "advisory"
                            else "review_required",
                        }
                    )
            state["sources"][source["id"]] = {
                "identity": identity,
                "seen": sorted(seen | fingerprints)[-2000:],
                "last_success": observed,
                "versions": [record["version"] for record in records],
                "revisions": [record["revision"] for record in records],
            }
            report["sources"].append(
                {"id": source["id"], "status": "ok", "observations": len(records)}
            )
        except (
            SourceError,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
            ParseError,
            DefusedXmlException,
        ) as error:
            code = (
                str(error)
                if isinstance(error, SourceError)
                else "invalid_source_response"
            )
            report["errors"].append({"source": source["id"], "code": code})
            report["sources"].append({"id": source["id"], "status": "failed"})
    report["success"] = not report["errors"]
    return report, state if report["success"] else None


def markdown(report):
    """Render bounded, sanitized observations and honest impact uncertainty."""
    lines = [
        "# Maintenance report",
        "",
        f"Observed: {report['observed_at']}",
        "",
        "Read-only. No issues, agent sessions, merges or releases created.",
        "",
        "| Source | Version / revision | Decision | Priority | Citation |",
        "| --- | --- | --- | --- | --- |",
    ]

    def cell(value):
        return (
            str(value)
            .replace("|", " ")
            .replace("\n", " ")
            .replace("<", "&lt;")
            .replace(">", "&gt;")[:200]
        )

    for item in report["findings"]:
        # URLs already passed public_link; escaping parentheses prevents link injection.
        url = item["url"].replace("(", "%28").replace(")", "%29")
        lines.append(
            f"| {cell(item['source'])} | {cell(item['version'])} | defer: review required | {item['priority']} | [source]({url}) |"
        )
    if not report["findings"]:
        lines.extend(
            ["", "No new observations relative to this configuration's saved snapshot."]
        )
    for error in report["errors"]:
        lines.extend(
            [
                "",
                f"Source failure: {cell(error['source'])}: {cell(error['code'])}. Review state was not advanced.",
            ]
        )
    lines.extend(
        [
            "",
            "All impacts, installed-version advisory exposure, benefits, effort and compatibility risk require human review; see report.json. No recommendation claims a change is safe to adopt automatically.",
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    """Run report-only monitoring and write state only after a complete snapshot."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--state", default=".maintenance-state/state.json")
    parser.add_argument("--output", default=".maintenance-output")
    args = parser.parse_args()
    config = validate(yaml.safe_load(Path(args.config).read_text()))
    prior = Path(args.state)
    previous = json.loads(prior.read_text()) if prior.exists() else None
    report, state = build_report(
        config, previous, lambda url: download(url, os.environ.get("GH_TOKEN", ""))
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "report.md").write_text(markdown(report))
    if state is not None:
        (output / "state.json").write_text(json.dumps(state, indent=2) + "\n")
    print(  # noqa: T201 - bounded CLI status, no source bodies or credentials
        f"Sources: {len(report['sources'])}; new observations: {len(report['findings'])}; failures: {len(report['errors'])}"
    )
    raise SystemExit(0 if report["success"] else 1)


if __name__ == "__main__":
    main()
