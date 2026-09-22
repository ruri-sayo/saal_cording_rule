import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.impl_aware


def run(cwd: Path, *args: str, env=None):
    values = os.environ.copy()
    values["PYTHONPATH"] = str(Path(__file__).parents[2] / "src")
    if env:
        values.update(env)
    return subprocess.run(
        [sys.executable, "-m", "saalco.cli", *args],
        cwd=cwd,
        env=values,
        text=True,
        capture_output=True,
        check=False,
    )


def test_init_new_and_approval_hash(tmp_path: Path):
    result = run(
        tmp_path,
        "init",
        "--name",
        "demo",
        "--type",
        "system",
        "--language",
        "python",
        "--non-interactive",
    )
    assert result.returncode == 0, result.stderr
    result = run(tmp_path, "new", "feature", "Login", "--tier", "S", "--slug", "login")
    assert result.stdout.strip() == "F-001"
    result = run(tmp_path, "new", "req", "Need login", "--feature", "F-001")
    assert result.stdout.strip() == "REQ-0001"
    req = tmp_path / "docs/features/F-001_login/10-requirements.md"
    result = run(
        tmp_path,
        "approve",
        str(req),
        env={"SAALCO_ALLOW_NONTTY_APPROVE": "1", "GIT_AUTHOR_NAME": "Test"},
    )
    # git config is deliberately required; configure locally and retry.
    if result.returncode:
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
        result = run(tmp_path, "approve", str(req), env={"SAALCO_ALLOW_NONTTY_APPROVE": "1"})
    assert result.returncode == 0, result.stderr
    req.write_text(req.read_text() + "changed\n")
    result = run(tmp_path, "check")
    assert result.returncode == 1
    assert "approved_hash does not match" in result.stdout
