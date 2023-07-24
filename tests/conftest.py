"""conftest"""
import shutil
from pathlib import Path
from typing import Any, Callable

import pytest
from click.testing import CliRunner, Result
from pdm.core import Core


@pytest.fixture(name="repo_path")
def fixture_repo_path(request: pytest.FixtureRequest) -> Path:
    """Test fixture returning path to current git repository.

    Args:
        request: pytest FixtureRequest from the calling module

    Returns:
        Path of this git repository.
    """
    return request.config.rootpath


@pytest.fixture(name="tests_base_path")
def fixture_tests_base_path(repo_path: Path) -> Path:
    """Get path to /tests

    Args:
        repo_path: path to git repo root

    Returns:
        Path to tests folder (calling module)
    """
    return repo_path.joinpath("tests")


@pytest.fixture(name="temp_dir")
def fixture_temp_dir(request: pytest.FixtureRequest, tests_base_path: Path) -> Path:
    """Test fixture to access a temp directory for the current test method.

    Args:
        request: pytest-internal fixture to access the current test function.
        tests_base_path: pytest fixture for path to tests directory

    Returns:
        Named directory for the test function where this fixture is used.
    """
    module_path = request.path.relative_to(tests_base_path)
    test_name = request.function.__name__
    temp_path = tests_base_path.joinpath("_temp", module_path, test_name)
    shutil.rmtree(temp_path, ignore_errors=True)
    temp_path.mkdir(exist_ok=True, parents=True)
    return temp_path


@pytest.fixture(name="data_base_path")
def fixture_data_base_path(tests_base_path: Path) -> Path:
    """Test fixture returning path to test/data directory.

    Args:
        tests_base_path: Path to tests directory

    Returns:
        Path to the 'tests/data' folder.
    """
    return tests_base_path.joinpath("data").resolve()


@pytest.fixture(scope="session")
def invoke() -> Callable[..., Result]:
    """Wrapper for CLIRunner"""
    runner = CliRunner(mix_stderr=False)

    def caller(args: Any) -> Result:
        return runner.invoke(Core(), args, prog_name="pdm", catch_exceptions=False)  # type: ignore[arg-type]

    return caller
