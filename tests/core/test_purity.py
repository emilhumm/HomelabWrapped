"""The core never imports Home Assistant, so a standalone version can reuse it as it is."""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys

import pytest

CORE = Path(__file__).parents[2] / "custom_components" / "homelab_wrapped" / "core"
MODULES = sorted(CORE.glob("*.py"))


@pytest.mark.parametrize("path", MODULES, ids=lambda path: path.name)
def test_imports_only_the_standard_library_and_itself(path: Path) -> None:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names = [node.module or ""]
        else:
            continue
        for name in names:
            top = name.split(".")[0]
            assert top in sys.stdlib_module_names or top == "__future__", (
                f"{path.name} imports {name}; the core may only import the standard "
                "library and its own modules (relatively)"
            )


def test_imports_as_a_standalone_package_without_home_assistant() -> None:
    """Import the core as a top-level package in a clean interpreter with HA blocked."""
    code = f"""
import sys

class BlockHomeAssistant:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] == "homeassistant":
            raise ImportError(name)

sys.meta_path.insert(0, BlockHomeAssistant())
sys.path.insert(0, {str(CORE.parent)!r})
import core.coverage, core.diagnostics, core.model, core.sources, core.tally, core.uptime
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
