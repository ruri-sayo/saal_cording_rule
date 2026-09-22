import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.impl_aware


def cli(
    root: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    values = {**os.environ, **(env or {})}
    return subprocess.run(
        ["saalco", *args], cwd=root, env=values, text=True, capture_output=True, check=False
    )


def test_installed_cli_workflow(tmp_path: Path):
    result = cli(
        tmp_path,
        "init",
        "--name",
        "sample",
        "--type",
        "research",
        "--language",
        "python",
        "--non-interactive",
    )
    assert result.returncode == 0, result.stderr
    assert (
        cli(tmp_path, "new", "feature", "Search", "--tier", "S", "--slug", "search").returncode == 0
    )
    assert cli(tmp_path, "new", "req", "Search works", "--feature", "F-001").returncode == 0
    assert cli(tmp_path, "new", "dd", "Search design", "--feature", "F-001").returncode == 0
    assert cli(tmp_path, "new", "ut", "Search unit spec", "--feature", "F-001").returncode == 0
    folder = tmp_path / "docs/features/F-001_search"
    req = folder / "10-requirements.md"
    dd = folder / "30-detailed-design.md"
    ut = folder / "40-unit-test-spec.md"
    req.write_text(req.read_text().replace("verify: test", "verify: review"))
    dd.write_text(
        dd.read_text()
        .replace("covers: \n", "covers: REQ-0001\n")
        .replace("verify: test", "verify: review")
    )
    ut.write_text(ut.read_text().replace("covers: \n", "covers: DD-0001\n"))
    subprocess.run(["git", "config", "user.name", "E2E Human"], cwd=tmp_path, check=True)
    approved = cli(
        tmp_path,
        "approve",
        str(folder / "00-meta.md"),
        str(req),
        str(dd),
        env={"SAALCO_ALLOW_NONTTY_APPROVE": "1"},
    )
    assert approved.returncode == 0, approved.stderr
    checked = cli(tmp_path, "check", "--json")
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert cli(tmp_path, "trace").returncode == 0
    assert (tmp_path / "docs/trace/rtm.csv").is_file()
