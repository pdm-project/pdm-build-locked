import hashlib
import re
from pathlib import Path

from pkginfo import Wheel


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
