"""Repository-local lesson validation and retrieval (SPEC #36)."""
import argparse
import json
import re
import sys
from pathlib import Path

STORE = Path(__file__).with_name("lessons.json")
FIELDS = {"id", "tags", "trigger", "evidence", "action", "status", "supersedes"}

def words(value):
    return set(re.findall(r"\w+", value.casefold()))

def normalized(value):
    return " ".join(re.findall(r"\w+", value.casefold()))

def validate(rows):
    if not isinstance(rows, list):
        raise ValueError("Expected a list")
    ids, fingerprints, replaced = set(), set(), set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError("Invalid lesson fields")
        for key in ("id", "trigger", "evidence", "action", "status"):
            if not isinstance(row[key], str) or not row[key].strip() or len(row[key]) > 1000:
                raise ValueError("Invalid field: " + key)
        if not isinstance(row["tags"], list) or not row["tags"] or not all(isinstance(t, str) and t.strip() for t in row["tags"]):
            raise ValueError("Invalid tags")
        if row["id"] in ids or row["status"] not in ("candidate", "approved", "retired"):
            raise ValueError("Duplicate ID or invalid status")
        if not re.fullmatch(r"(?:https://github\.com/[^/\s]+/[^/\s]+/(?:issues|pull|commit)/[a-zA-Z0-9]+|[a-f0-9]{40})", row["evidence"]):
            raise ValueError("Evidence must reference an issue, PR or commit")
        if row["supersedes"] is not None:
            if not isinstance(row["supersedes"], str) or row["supersedes"] not in ids:
                raise ValueError("Supersession must reference an earlier lesson")
            if row["status"] == "approved":
                if row["supersedes"] in replaced:
                    raise ValueError("Ambiguous supersession")
                replaced.add(row["supersedes"])
        # Heuristic only; human review remains mandatory.
        payload = " ".join([row["id"], *row["tags"], row["trigger"], row["action"]])
        if re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:ghp_|github_pat_|sk-)[A-Za-z0-9_-]{16,}|(?:password|api[_ -]?key|token|secret)\s*[:=]\s*\S{8,}", payload, re.I):
            raise ValueError("Potential credential in lesson")
        fp = (normalized(row["trigger"]), normalized(row["action"]))
        if fp in fingerprints:
            raise ValueError("Duplicate lesson")
        fingerprints.add(fp)
        ids.add(row["id"])
    return replaced

def retrieve(rows, query, budget=2000, limit=5):
    replaced = validate(rows)
    if budget < 2 or limit < 0:
        raise ValueError("Invalid retrieval bounds")
    terms = words(query)
    matches = []
    for row in rows:
        if row["status"] != "approved" or row["id"] in replaced:
            continue
        score = len(terms & words(" ".join(row["tags"]))) * 3 + len(terms & words(row["trigger"]))
        if score:
            matches.append((-score, row["id"], row))
    result = []
    for _, _, row in sorted(matches):
        if len(result) >= limit:
            break
        candidate = result + [row]
        if len(json.dumps(candidate, ensure_ascii=True)) <= budget:
            result = candidate
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["validate", "retrieve"])
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--budget", type=int, default=2000)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    try:
        rows = json.loads(STORE.read_text(encoding="utf-8"))
        validate(rows)
        if args.command == "retrieve":
            if args.budget < 2:
                raise ValueError("Budget must fit an empty JSON array")
            print(json.dumps(retrieve(rows, args.query, args.budget, args.limit), ensure_ascii=True))
        else:
            print("OK")
    except (OSError, ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
