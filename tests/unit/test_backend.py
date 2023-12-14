from pathlib import Path

import pytest
from pkginfo import Wheel


def build_wheel(src_dir: Path, wheel_dir: Path) -> Wheel:
    from build.__main__ import build_package

    result = build_package(src_dir, wheel_dir, ["wheel"], isolation=False)
    return Wheel(str(wheel_dir / result[0]))


@pytest.mark.usefixtures("assert_pyproject_unmodified")
@pytest.mark.parametrize("test_project", ["lock"])
def test_pdm_backend(temp_dir: Path, data_base_path: Path, test_project: str) -> None:
    project = data_base_path / test_project
    wheel = build_wheel(project, temp_dir)
    assert set(wheel.requires_dist) == {
        "requests",
        'certifi==2023.11.17; extra == "locked"',
        'charset-normalizer==3.3.2; extra == "locked"',
        'requests==2.31.0; extra == "locked"',
        'urllib3==2.1.0; extra == "locked"',
        'idna==3.6; extra == "locked"',
    }


@pytest.mark.usefixtures("assert_pyproject_unmodified")
@pytest.mark.parametrize("test_project", ["lock-disabled"])
def test_pdm_backend_disabled(temp_dir: Path, data_base_path: Path, test_project: str) -> None:
    project = data_base_path / test_project
    wheel = build_wheel(project, temp_dir)
    assert set(wheel.requires_dist) == {"requests"}


@pytest.mark.usefixtures("assert_pyproject_unmodified")
@pytest.mark.parametrize("test_project", ["lock-disabled"])
def test_pdm_backend_enabled(
    temp_dir: Path, data_base_path: Path, test_project: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PDM_BUILD_LOCKED", "true")
    project = data_base_path / test_project
    wheel = build_wheel(project, temp_dir)
    assert set(wheel.requires_dist) == {
        "requests",
        'certifi==2023.11.17; extra == "locked"',
        'charset-normalizer==3.3.2; extra == "locked"',
        'requests==2.31.0; extra == "locked"',
        'urllib3==2.1.0; extra == "locked"',
        'idna==3.6; extra == "locked"',
    }


@pytest.mark.usefixtures("assert_pyproject_unmodified")
@pytest.mark.parametrize("test_project", ["lock-hatchling"])
def test_hatchling_backend(temp_dir: Path, data_base_path: Path, test_project: str) -> None:
    project = data_base_path / test_project
    wheel = build_wheel(project, temp_dir)
    assert set(wheel.requires_dist) == {
        "requests",
        "certifi==2023.11.17; extra == 'locked'",
        "charset-normalizer==3.3.2; extra == 'locked'",
        "requests==2.31.0; extra == 'locked'",
        "urllib3==2.1.0; extra == 'locked'",
        "idna==3.6; extra == 'locked'",
    }


@pytest.mark.usefixtures("assert_pyproject_unmodified")
@pytest.mark.parametrize("test_project", ["lock", "lock-hatchling"])
def test_backend_lockfile_unsupported(
    temp_dir: Path, data_base_path: Path, monkeypatch: pytest.MonkeyPatch, test_project: str
) -> None:
    monkeypatch.setenv("PDM_LOCKFILE", "pdm.legacy.lock")
    project = data_base_path / test_project
    wheel = build_wheel(project, temp_dir)
    assert set(wheel.requires_dist) == {"requests"}


@pytest.mark.usefixtures("assert_pyproject_unmodified")
@pytest.mark.parametrize("test_project", ["simple", "simple-hatchling"])
def test_backend_no_lockfile(
    temp_dir: Path, data_base_path: Path, monkeypatch: pytest.MonkeyPatch, test_project: str
) -> None:
    project = data_base_path / test_project
    wheel = build_wheel(project, temp_dir)
    assert set(wheel.requires_dist) == {"requests==2.31.0"}
