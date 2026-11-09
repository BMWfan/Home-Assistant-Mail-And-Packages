"""Select prior state only for the same repository, ref and configuration bytes."""

import hashlib
import json
import os
from pathlib import Path

from monitor import REPOSITORY, download


def main():
    """Emit only an artifact name and optional previous run ID, never a token."""
    repo = os.environ["GITHUB_REPOSITORY"]
    if not REPOSITORY.fullmatch(repo):
        raise ValueError("invalid_repository")
    identity = (
        repo.encode()
        + os.environ["GITHUB_REF"].encode()
        + Path(os.environ["MONITOR_CONFIG"]).read_bytes()
    )
    name = "maintenance-state-" + hashlib.sha256(identity).hexdigest()[:20]
    data = json.loads(
        download(
            f"https://api.github.com/repos/{repo}/actions/artifacts?per_page=100&name={name}",
            os.environ["GH_TOKEN"],
        )
    )
    run_id = ""
    for artifact in data["artifacts"]:
        candidate = artifact.get("workflow_run", {}).get("id")
        if (
            artifact["name"] == name
            and not artifact["expired"]
            and str(candidate) != os.environ["GITHUB_RUN_ID"]
        ):
            if not isinstance(candidate, int) or candidate <= 0:
                raise ValueError("invalid_previous_run")
            run_id = str(candidate)
            break
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"name={name}\nrun_id={run_id}\n")


if __name__ == "__main__":
    main()
