from __future__ import annotations

from typing import Any

import pytest

from pdm_build_locked._utils import UnsupportedRequirement, get_locked_group_name, requirement_dict_to_string


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
