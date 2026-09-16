from __future__ import annotations

from pathlib import Path

import tomllib


def test_flat_layout_and_dynamic_version() -> None:
    root = Path(__file__).parents[1]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert not (root / "src").exists()
    assert data["project"]["dynamic"] == ["version"]
    assert "version" not in data["project"]
    assert data["tool"]["setuptools_scm"]["write_to"] == "espeakng_runtime/_version.py"
    assert data["tool"]["setuptools_scm"]["fallback_version"] == "0.1.dev0"
