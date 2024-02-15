"""test pdm build --locked"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.utils import count_group_dependencies, wheel_from_tempdir

if TYPE_CHECKING:
    from pdm.pytest import PDMCallable


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
@pytest.mark.parametrize("test_project", ["simple"])
def test_build_locked_env(
    pdm: PDMCallable, data_base_path: Path, temp_dir: Path, test_project: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Build a project with PDM_BUILD_LOCKED=1 in the environment

    Args:
        pdm: PDM runner fixture
        data_base_path: path to tests/data
        temp_dir: path to tests/_temp/... temporary directory
        test_project: path to test project
    """
    monkeypatch.setenv("PDM_BUILD_LOCKED", "1")
    project_path = data_base_path.joinpath(test_project)
    cmd = ["build", "--project", project_path.as_posix(), "--dest", temp_dir.as_posix()]
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


@pytest.mark.usefixtures("assert_pyproject_unmodified")
@pytest.mark.parametrize("test_project", ["empty"])
def test_build_locked_empty(pdm: PDMCallable, data_base_path: Path, temp_dir: Path, test_project: str) -> None:
    """this project's lockfile has empty dependencies and dynamic optional-dependencies
    doesn't make sense to use the plugin in this case - but it should work nevertheless

    Args:
        pdm: PDM runner fixture
        data_base_path: path to tests/data
        temp_dir: path to tests/_temp/... temporary directory
        test_project: path to test project
    """
    project_path = data_base_path.joinpath(test_project)
    cmd = [
        "build",
        "--locked",
        "--project",
        project_path.as_posix(),
        "--dest",
        temp_dir.as_posix(),
    ]
    result = pdm(cmd)
    assert result.exit_code == 0
