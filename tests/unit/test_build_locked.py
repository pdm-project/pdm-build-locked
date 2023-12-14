"""test pdm build --locked"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import pytest
from pkginfo import Wheel

if TYPE_CHECKING:
    from pdm.pytest import PDMCallable


def wheel_from_tempdir(whl_dir: Path) -> Wheel:
    """
    read Wheel metadata from built wheel

    Args:
        whl_dir: location of wheel

    Returns:
        pkginfo Wheel object

    Raises:
        AssertionError: if no whl file is found in the expected location
    """
    assert any(whl_dir.iterdir())
    for file in whl_dir.iterdir():
        if file.suffix == ".whl":
            return Wheel(file.as_posix())

    raise AssertionError(f"No .whl file found at {whl_dir}")


def count_group_dependencies(wheel: Wheel, group_name: str) -> int:
    """
    count *exact* group dependencies in wheel requires_dist using regex
    `group_name` is only detected if it is fully enclosed by quotes in the requires_dist entry

    Args:
        wheel: the pkginfo Wheel object
        group_name: exact name of the optional dependency group

    Returns:

    """
    return sum(1 for dist in wheel.requires_dist if re.search(rf"[\"\']{group_name}[\"\']", dist))


def get_pyproject_hash(project: Path) -> str:
    """
    Hash the pyproject file using sha256

    Args:
        project: path to the project root

    Returns:
        sha256 of pyproject.toml file contents
    """
    with open(project.joinpath("pyproject.toml"), "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()  # when >=3.11: use hashlib.file_digest instead


@pytest.fixture
def assert_pyproject_unmodified(data_base_path: Path, test_project: str) -> Generator[None, None, None]:
    """
    A pytest fixture to assert that pyproject.toml is reset properly to its original state
    """
    project = data_base_path / test_project
    hash_before = get_pyproject_hash(project)
    yield
    assert get_pyproject_hash(project) == hash_before, "pyproject.toml hashes do not match, check for modifications"


@pytest.mark.usefixtures("assert_pyproject_unmodified")
@pytest.mark.parametrize("test_project", ["simple-optional"])
def test_build_locked_optional(pdm: PDMCallable, data_base_path: Path, temp_dir: Path, test_project: str) -> None:
    """this project has optional dependencies, is not yet locked and has no setting in pyproject.toml

    Args:
        pdm: PDM runner fixture
        data_base_path: path to tests/data
        temp_dir: path to tests/_temp/... temporary directory
        test_project: path to test project
    """
    project_path = data_base_path.joinpath(test_project)
    cmd = ["build", "--locked", "--project", project_path.as_posix(), "--dest", temp_dir.as_posix()]
    result = pdm(cmd)
    assert result.exit_code == 0
    project_path.joinpath("pdm.lock").unlink()

    wheel = wheel_from_tempdir(temp_dir)
    assert count_group_dependencies(wheel, "locked") == 5
    assert count_group_dependencies(wheel, "socks-locked") == 1
    assert count_group_dependencies(wheel, "test-locked") == 0  # dev-dependency test group should be skipped


@pytest.mark.usefixtures("assert_pyproject_unmodified")
@pytest.mark.parametrize("test_project", ["simple"])
def test_build_locked(pdm: PDMCallable, data_base_path: Path, temp_dir: Path, test_project: str) -> None:
    """this project has no optional dependencies, is not yet locked and has no setting in pyproject.toml

    Args:
        pdm: PDM runner fixture
        data_base_path: path to tests/data
        temp_dir: path to tests/_temp/... temporary directory
        test_project: path to test project
    """
    project_path = data_base_path.joinpath(test_project)
    cmd = ["build", "--locked", "--project", project_path.as_posix(), "--dest", temp_dir.as_posix()]
    result = pdm(cmd)
    assert result.exit_code == 0
    project_path.joinpath("pdm.lock").unlink()

    wheel = wheel_from_tempdir(temp_dir)
    assert sum(1 for dist in wheel.requires_dist if "locked" in dist) == 5


@pytest.mark.usefixtures("assert_pyproject_unmodified")
@pytest.mark.parametrize("test_project", ["simple-optional"])
def test_build_normal(pdm: PDMCallable, data_base_path: Path, temp_dir: Path, test_project: str) -> None:
    """test that not using --locked doesn't add locked dependencies

    Args:
        pdm: PDM runner fixture
        data_base_path: path to tests/data
        temp_dir: path to tests/_temp/... temporary directory
        test_project: path to test project
    """
    project_path = data_base_path.joinpath(test_project)
    cmd = ["build", "--project", project_path.as_posix(), "--dest", temp_dir.as_posix()]
    result = pdm(cmd)
    assert result

    wheel = wheel_from_tempdir(temp_dir)
    assert not any("locked" in dist for dist in wheel.requires_dist)


@pytest.mark.usefixtures("assert_pyproject_unmodified")
@pytest.mark.parametrize("test_project", ["large"])
def test_build_locked_pyproject(pdm: PDMCallable, data_base_path: Path, temp_dir: Path, test_project: str) -> None:
    """this project has a lockfile and the pyproject.toml setting tool.pdm.build.locked

    Args:
        pdm: PDM runner fixture
        data_base_path: path to tests/data
        temp_dir: path to tests/_temp/... temporary directory
        test_project: path to test project
    """
    project_path = data_base_path.joinpath(test_project).as_posix()
    cmd = ["build", "--project", project_path, "--dest", temp_dir.as_posix()]
    result = pdm(cmd)
    assert result.exit_code == 0

    wheel = wheel_from_tempdir(temp_dir)
    assert count_group_dependencies(wheel, "locked") == 26
    assert count_group_dependencies(wheel, "extras-locked") == 1
    assert count_group_dependencies(wheel, "cow-locked") == 1


@pytest.mark.usefixtures("assert_pyproject_unmodified")
@pytest.mark.parametrize("test_project", ["invalid"])
def test_build_locked_invalid(pdm: PDMCallable, data_base_path: Path, temp_dir: Path, test_project: str) -> None:
    """this project's lockfile has a group containing "-locked" and will thus error

    Args:
        pdm: PDM runner fixture
        data_base_path: path to tests/data
        temp_dir: path to tests/_temp/... temporary directory
        test_project: path to test project
    """
    project_path_invalid = data_base_path.joinpath(test_project)
    cmd = [
        "build",
        "--locked",
        "--project",
        project_path_invalid.as_posix(),
        "--dest",
        temp_dir.as_posix(),
    ]
    result = pdm(cmd)
    assert "PdmException" in result.stderr
