"""Tests for the ade-based collection install workflow."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

from configparser import ConfigParser
from pathlib import Path

import pytest

from tests.conftest import run


def test_ade_workflow_config(
    module_fixture_dir: Path,
    tox_bin: Path,
) -> None:
    """Validate generated tox config uses ade for collection installation.

    Args:
        module_fixture_dir: pytest fixture for module fixture directory
        tox_bin: pytest fixture for tox binary
    """
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    try:
        proc = run(
            f"{tox_bin} config --ansible --root {module_fixture_dir} --conf tox-ansible.ini -qq",
            cwd=module_fixture_dir,
            check=True,
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        print(exc.stdout)
        print(exc.stderr)
        pytest.fail(exc.stderr)

    cfg_parser = ConfigParser()
    cfg_parser.read_string(proc.stdout)

    for env_name in cfg_parser.sections():
        if env_name == "testenv:galaxy":
            continue

        config = dict(cfg_parser[env_name])
        is_sanity = "sanity" in env_name
        assert "ade install" in config["commands_pre"], (
            f"{env_name}: commands_pre should contain 'ade install'"
        )
        if is_sanity:
            assert "ade install -e" not in config["commands_pre"], (
                f"{env_name}: sanity commands_pre must not use editable install"
            )
        else:
            assert "ade install -e" in config["commands_pre"], (
                f"{env_name}: commands_pre should use editable install"
            )
        assert "ansible-dev-environment>=26.2.0" in config["deps"], (
            f"{env_name}: deps should contain 'ansible-dev-environment>=26.2.0'"
        )
        assert "ade" in config["allowlist_externals"], (
            f"{env_name}: allowlist_externals should contain 'ade'"
        )
        if "integration" in env_name:
            assert "ANSIBLE_COLLECTIONS_PATH" not in config["set_env"]
            assert "MOLECULE_GLOB" not in config["set_env"]
            assert "python3 -m molecule" in config["commands"]
            assert "test --all" in config["commands"]
            assert "molecule>=26.4.0" in config["deps"]
            assert "pytest-ansible>=v4.1.1" not in config["deps"]
            generated_config = (
                module_fixture_dir
                / ".tox/.tox-ansible/molecule"
                / f"{env_name.removeprefix('testenv:')}.yml"
            )
            assert generated_config.read_text() == "---\nprerun: false\n"
        else:
            assert "ANSIBLE_COLLECTIONS_PATH=." in config["set_env"], (
                f"{env_name}: set_env should contain 'ANSIBLE_COLLECTIONS_PATH=.'"
            )


def test_ade_workflow_collection_requirements(
    module_fixture_dir: Path,
    tox_bin: Path,
) -> None:
    """Validate commands_pre installs collection requirements from tests/.

    Args:
        module_fixture_dir: pytest fixture for module fixture directory
        tox_bin: pytest fixture for tox binary
    """
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    try:
        proc = run(
            f"{tox_bin} config --ansible --root {module_fixture_dir} --conf tox-ansible.ini -qq",
            cwd=module_fixture_dir,
            check=True,
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        print(exc.stdout)
        print(exc.stderr)
        pytest.fail(exc.stderr)

    cfg_parser = ConfigParser()
    cfg_parser.read_string(proc.stdout)

    for env_name in cfg_parser.sections():
        config = dict(cfg_parser[env_name])
        commands_pre = config.get("commands_pre", "")

        if "unit" in env_name or "integration" in env_name:
            assert "ade install -r tests/requirements.yml" in commands_pre, (
                f"{env_name}: commands_pre should install tests/requirements.yml"
            )
        elif "sanity" in env_name or "galaxy" in env_name:
            assert "ade install -r" not in commands_pre, (
                f"{env_name}: commands_pre should not install collection requirements"
            )


@pytest.mark.parametrize("config_format", ("ini", "toml"))
def test_ade_workflow_coverage_config(
    config_format: str,
    module_fixture_dir: Path,
    tmp_path: Path,
    tox_bin: Path,
) -> None:
    """Validate INI and TOML configuration enable unit coverage only.

    Args:
        config_format: The tox-ansible configuration format to test.
        module_fixture_dir: Pytest fixture for the module fixture directory.
        tmp_path: Pytest fixture for a temporary directory.
        tox_bin: Pytest fixture for the tox binary.
    """
    collection_dir = tmp_path / config_format
    shutil.copytree(module_fixture_dir, collection_dir)
    if config_format == "ini":
        with (collection_dir / "tox-ansible.ini").open("a") as config_file:
            config_file.write("\n[ansible]\ncoverage = true\n")
    else:
        (collection_dir / "pyproject.toml").write_text(
            '[tool.tox]\nrequires = ["tox>=4.2"]\n\n[tool.tox-ansible]\ncoverage = true\n',
        )

    proc = run(
        f"{tox_bin} config --ansible --root {collection_dir} --conf tox-ansible.ini "
        "-e unit-py3.13-2.19,integration-py3.13-2.19 -k commands deps -qq",
        cwd=collection_dir,
        check=True,
        timeout=10,
    )
    cfg_parser = ConfigParser()
    cfg_parser.read_string(proc.stdout)
    unit = cfg_parser["testenv:unit-py3.13-2.19"]
    integration = cfg_parser["testenv:integration-py3.13-2.19"]
    coverage_config = collection_dir / ".tox/.tox-ansible/coverage/unit-py3.13-2.19.ini"

    assert "coverage>=7.0.0" in unit["deps"]
    assert "pytest-cov>=4.1.0" in unit["deps"]
    assert "--cov --cov-config=" in unit["commands"]
    assert coverage_config.is_file()
    coverage_content = coverage_config.read_text()
    assert "source =\n    plugins\n" in coverage_content
    assert "ansible_collections/test_ns/test_col/plugins" in coverage_content
    assert "include_namespace_packages = true" in coverage_content
    assert f"data_file = {collection_dir}/.tox/unit-py3.13-2.19/.coverage" in coverage_content
    assert "pytest-cov" not in integration["deps"]
    assert "--cov" not in integration["commands"]
    assert not (collection_dir / ".coveragerc").exists()


def test_ade_workflow_molecule_config_and_dependencies(
    module_fixture_dir: Path,
    tmp_path: Path,
    tox_bin: Path,
) -> None:
    """Validate existing Molecule config and Python requirements are preserved."""
    collection_dir = tmp_path / "collection"
    shutil.copytree(module_fixture_dir, collection_dir)
    base_config = collection_dir / "extensions/molecule/config.yml"
    base_config.parent.mkdir(parents=True)
    base_config.write_text("---\nlog: true\n")
    python_requirements = collection_dir / "tests/integration/requirements.txt"
    python_requirements.parent.mkdir(parents=True, exist_ok=True)
    python_requirements.write_text("molecule-plugins[docker]\n")

    proc = run(
        f"{tox_bin} config --ansible --root {collection_dir} --conf tox-ansible.ini "
        "-e integration-py3.13-2.19 -k commands commands_pre deps set_env -qq",
        cwd=collection_dir,
        check=True,
        timeout=10,
    )
    cfg_parser = ConfigParser()
    cfg_parser.read_string(proc.stdout)
    integration = cfg_parser["testenv:integration-py3.13-2.19"]
    generated_config = collection_dir / ".tox/.tox-ansible/molecule/integration-py3.13-2.19.yml"

    assert integration["commands"].index(str(base_config)) < integration["commands"].index(
        str(generated_config),
    )
    assert "molecule-plugins[docker]" in integration["deps"]
    assert "ade install -r tests/requirements.yml" in integration["commands_pre"]
    assert "ANSIBLE_COLLECTIONS_PATH" not in integration["set_env"]


@pytest.mark.slow
def test_ade_workflow_e2e(
    module_fixture_dir: Path,
    tmp_path: Path,
) -> None:
    """Run a full tox --ansible workflow in an isolated venv.

    Copies the fixture collection to a temp directory, creates a fresh venv,
    installs tox + tox-ansible + ade, and runs a unit test environment end-to-end.
    This mimics exactly what a real user would do.

    Args:
        module_fixture_dir: pytest fixture for module fixture directory
        tmp_path: pytest fixture for temporary directory
    """
    repo_root = Path(__file__).resolve().parents[2]

    collection_dir = tmp_path / "collection"
    shutil.copytree(module_fixture_dir, collection_dir)

    venv_dir = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True,
        capture_output=True,
    )

    pip = str(venv_dir / "bin" / "pip")
    tox_bin = str(venv_dir / "bin" / "tox")

    result = subprocess.run(
        [pip, "install", "tox", "-e", str(repo_root)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    py_minor = sys.version_info.minor
    py_ver = f"{sys.version_info.major}.{py_minor}"
    core_ver = {10: "2.17", 11: "2.19", 12: "2.19", 13: "2.19", 14: "2.20"}.get(
        py_minor,
        "2.19",
    )
    env_name = f"unit-py{py_ver}-{core_ver}"

    proc = subprocess.run(
        [tox_bin, "--ansible", "--coverage", "--conf", "tox-ansible.ini", "-e", env_name],
        check=False,
        cwd=str(collection_dir),
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, f"tox run failed:\n{proc.stdout}\n{proc.stderr}"
    assert "plugins/modules/hello.py" in proc.stdout
    assert re.search(
        r"plugins/module_utils/untested\.py\s+\d+\s+\d+\s+0%",
        proc.stdout,
    )
    assert "site-packages/ansible_collections/test_ns/test_col/plugins" not in proc.stdout
    assert (collection_dir / ".tox" / env_name / ".coverage").is_file()
    assert not (collection_dir / ".coverage").exists()
    assert not (collection_dir / ".coveragerc").exists()
