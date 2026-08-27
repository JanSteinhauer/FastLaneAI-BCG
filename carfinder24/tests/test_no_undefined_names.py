"""Every name the agent's own code uses must actually exist.

This exists because of a real defect: a merge deleted a helper that
`used_car_advisor.tools` still called, and it went unnoticed because the suite
only exercises the MCP tools. The wrappers around them are only reached through
a live voice session, so a NameError in one is invisible until a customer hits
it — which is exactly what happened: every attempt to open a single car's card
crashed, and the advisor said it was "having technical trouble".

Ruff's F rules (F821 undefined name, F811 redefinition, F401 unused import)
catch that class of error in the second it takes to run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("target", ["src", "tests"])
def test_no_undefined_or_duplicate_names(target: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", target, "--select", "F"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"ruff found problems in {target}/:\n{result.stdout}"
