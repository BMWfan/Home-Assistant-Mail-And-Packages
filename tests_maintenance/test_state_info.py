"""State selection is scoped and never silently ignores restore/API failures."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ACTION = Path(__file__).parents[1] / ".github/actions/maintenance-monitor"
sys.path.insert(0, str(ACTION))
spec = importlib.util.spec_from_file_location("state_info", ACTION / "state_info.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class StateTests(unittest.TestCase):
    def test_new_project_baseline_and_existing_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.yml"
            config.write_text("version: 1")
            output = Path(directory) / "output"
            env = {
                "GITHUB_REPOSITORY": "owner/project",
                "GITHUB_REF": "refs/heads/main",
                "GITHUB_RUN_ID": "42",
                "GH_TOKEN": "synthetic",
                "MONITOR_CONFIG": str(config),
                "GITHUB_OUTPUT": str(output),
            }
            with (
                patch.dict(os.environ, env),
                patch.object(m, "download", return_value=b'{"artifacts": []}'),
            ):
                m.main()
                initial = output.read_text()
                name = initial.splitlines()[0].split("=", 1)[1]
                self.assertIn("run_id=\n", initial)
                output.write_text("")
                artifact = {"name": name, "expired": False, "workflow_run": {"id": 9}}
                with patch.object(
                    m,
                    "download",
                    return_value=json.dumps({"artifacts": [artifact]}).encode(),
                ):
                    m.main()
                self.assertIn("run_id=9\n", output.read_text())
                output.write_text("")
                env["GITHUB_REF"] = "refs/heads/feature"
                with patch.dict(os.environ, env):
                    m.main()
                self.assertNotIn(name, output.read_text())

    def test_api_failure_propagates_instead_of_baselining(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.yml"
            config.write_text("version: 1")
            env = {
                "GITHUB_REPOSITORY": "owner/project",
                "GITHUB_REF": "refs/heads/main",
                "GITHUB_RUN_ID": "42",
                "GH_TOKEN": "synthetic",
                "MONITOR_CONFIG": str(config),
                "GITHUB_OUTPUT": str(Path(directory) / "output"),
            }
            with (
                patch.dict(os.environ, env),
                patch.object(m, "download", side_effect=RuntimeError("offline")),
            ):
                with self.assertRaises(RuntimeError):
                    m.main()
                self.assertFalse(Path(env["GITHUB_OUTPUT"]).exists())
