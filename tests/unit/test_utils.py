from __future__ import annotations

from typing import Any

import pytest

from pdm_build_locked._utils import (
    IncompatibleLockedRequirement,
    UnsupportedRequirement,
    check_locked_requirement_compatible,
    get_locked_group_name,
    requirement_dict_to_string,
)


@pytest.mark.parametrize("group,locked_group", [("default", "locked"), ("foo", "foo-locked")])
def test_get_locked_group_name(group: str, locked_group: str):
    assert get_locked_group_name(group) == locked_group


@pytest.mark.parametrize(
    "req,expected",
    [
        (
            {"name": "colorama", "version": "0.4.6"},
            "colorama==0.4.6",
        ),
        (
            {"name": "colorama", "version": "0.4.6", "extras": ["sec", "test"]},
            "colorama[sec,test]==0.4.6",
        ),
        (
            {
                "name": "colorama",
                "version": "0.4.6",
                "extras": ["sec", "test"],
                "marker": 'sys_platform == "win32"',
            },
            'colorama[sec,test]==0.4.6 ; sys_platform == "win32"',
        ),
        (
            {"name": "foo", "url": "https://packages.org/foo-0.4.0.tar.gz", "extras": ["sec", "test"]},
            "foo[sec,test] @ https://packages.org/foo-0.4.0.tar.gz",
        ),
        (
            {
                "name": "foo",
                "url": "https://packages.org/foo-0.4.0.tar.gz",
                "extras": ["sec", "test"],
                "marker": 'python_version >= "3.9"',
            },
            'foo[sec,test] @ https://packages.org/foo-0.4.0.tar.gz ; python_version >= "3.9"',
        ),
        (
            {"name": "foo", "git": "https://github.com/someone/foo.git", "extras": ["sec", "test"], "ref": "dev"},
            "foo[sec,test] @ git+https://github.com/someone/foo.git@dev",
        ),
        (
            {
                "name": "foo",
                "git": "https://github.com/someone/foo.git",
                "extras": ["sec", "test"],
                "ref": "dev",
                "revision": "0123456789abc",
            },
            "foo[sec,test] @ git+https://github.com/someone/foo.git@0123456789abc",
        ),
        (
            {
                "name": "foo",
                "git": "https://github.com/someone/foo.git",
                "extras": ["sec", "test"],
                "ref": "dev",
                "revision": "0123456789abc",
                "subdirectory": "subpath",
                "marker": 'python_version >= "3.9"',
            },
            "foo[sec,test] @ git+https://github.com/someone/foo.git"
            '@0123456789abc#subdirectory=subpath ; python_version >= "3.9"',
        ),
    ],
)
def test_requirement_dict_to_string(req: dict[str, Any], expected: str):
    assert requirement_dict_to_string(req) == expected


@pytest.mark.parametrize(
    "req,error",
    [
        ({"version": "0.4.6"}, "Missing name"),
        ({"name": "colorama", "path": "./subpath"}, "Local path requirement is not allowed"),
        (
            {"name": "colorama", "url": "https://packages.org/foo-0.4.0.tar.gz", "editable": True},
            "Editable requirement is not allowed",
        ),
    ],
)
def test_requirement_dict_to_string_illegal(req: dict[str, Any], error: str):
    with pytest.raises(UnsupportedRequirement, match=error):
        requirement_dict_to_string(req)


def test_check_locked_requirement_compatible_no_conflict():
    check_locked_requirement_compatible("sphinx==7.1.2", ["sphinx>=7.1.2"], "default")


def test_check_locked_requirement_compatible_no_matching_base_requirement():
    # e.g. a transitive dependency that isn't declared anywhere in the base requirements
    check_locked_requirement_compatible("certifi==2023.11.17", ["requests"], "default")


def test_check_locked_requirement_compatible_unversioned_base_requirement():
    check_locked_requirement_compatible("requests==2.31.0", ["requests"], "default")


def test_check_locked_requirement_compatible_not_pinned():
    # e.g. a URL/VCS requirement, which has no exact version to check
    check_locked_requirement_compatible("foo @ https://packages.org/foo-0.4.0.tar.gz", ["foo>=1.0"], "default")


def test_check_locked_requirement_compatible_conflict():
    with pytest.raises(IncompatibleLockedRequirement, match=r"sphinx==6\.2\.1.*default.*sphinx>7"):
        check_locked_requirement_compatible("sphinx==6.2.1", ["sphinx>7"], "default")
