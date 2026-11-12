# Copyright (c) PyWhy contributors. All rights reserved.
# Licensed under the MIT License.

"""Keep package metadata and CI interpreters in sync."""

from pathlib import Path

import pytest
import tomli
import yaml
from packaging.specifiers import SpecifierSet

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = ROOT / ".github" / "workflows"
PROJECT = tomli.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
SUPPORTED = SpecifierSet(PROJECT["requires-python"])


@pytest.mark.parametrize("workflow", sorted(WORKFLOWS.glob("*.yml")), ids=lambda path: path.name)
def test_ci_interpreters_match_package_support(workflow):
    """Require literal setup-python versions and matrix versions to satisfy Requires-Python.

    Check matrix axes and include entries in every workflow, leaving expression-based
    setup-python versions to their corresponding matrix checks.
    """
    for job in yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"].values():
        matrix = job.get("strategy", {}).get("matrix", {})
        for field in ("python-version", "version"):
            for version in matrix.get(field, []):
                assert version in SUPPORTED, f"{workflow.name}: unsupported matrix interpreter {version}"
            for cell in matrix.get("include", []):
                if field in cell:
                    assert cell[field] in SUPPORTED
        for step in job.get("steps", []):
            if str(step.get("uses", "")).startswith("actions/setup-python@"):
                version = str(step.get("with", {}).get("python-version", ""))
                if version and not version.startswith("${{"):
                    assert version in SUPPORTED, f"{workflow.name}: unsupported setup interpreter {version}"


def test_test_matrix_covers_advertised_python_versions():
    """Match the test matrix to Python classifiers, retaining 3.10 and rejecting 3.9 in metadata."""
    ci = yaml.safe_load((WORKFLOWS / "ci.yml").read_text(encoding="utf-8"))
    versions = set(ci["jobs"]["tests"]["strategy"]["matrix"]["python-version"])
    advertised = {
        classifier.removeprefix("Programming Language :: Python :: ")
        for classifier in PROJECT["classifiers"]
        if classifier.startswith("Programming Language :: Python :: ")
    }
    assert versions == advertised
    assert "3.10" in versions
    assert "3.9" not in SUPPORTED
