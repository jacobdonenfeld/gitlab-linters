from __future__ import annotations

import os

import pytest

from pre_commit_hooks.gitlab_ci_lint import call_ci_check


@pytest.mark.skip(reason="not figured out how to make correct api calls")
@pytest.mark.parametrize(
    ("test_file_path", "expected"),
    (
        ("valid_yaml/valid_1.yml", 0),
        ("valid_yaml/valid_2.yml", 0),
        ("valid_yaml/valid_3.yml", 0),
        ("valid_yaml/valid_4.yml", 0),
        ("valid_yaml/valid_5.yml", 0),
    ),
)
def test_yml_files(test_file_path, expected):
    """

    Test sending yml files to gitlab ci lint api
    """
    assert (
        call_ci_check([str(os.path.join("tests", "resources", test_file_path))])
        == expected
    )
