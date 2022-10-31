from __future__ import annotations

import os

import pytest
from git import Repo

from pre_commit_hooks import gitlab_script_check


@pytest.fixture(autouse=True)
def run_around_tests():
    """Start each test from git repo root directory"""
    git_root = Repo(".", search_parent_directories=True).working_tree_dir
    # set working directory to base of git repo
    os.chdir(str(git_root))


@pytest.mark.parametrize(
    ("test_file_path", "extra_args", "expected"),
    (
        ("import_chain_1/.gitlab-ci.yml", {"severity": "warning"}, 0),
        ("import_chain_2/.gitlab-ci.yml", {"severity": "warning"}, 1),
        ("import_chain_3/.gitlab-ci.yml", {"severity": "warning"}, 0),
    ),
)
def test_large_import_files(test_file_path, extra_args, expected):

    args = {
        "root-file": str(
            os.path.join("tests", "resources", "test_imports", test_file_path)
        )
    }
    args.update(extra_args)
    assert gitlab_script_check.call_ci_script_check(args) == expected


@pytest.mark.parametrize(
    ("test_file_path", "extra_args", "expected"),
    (
        ("valid_1.yml", {"severity": "warning"}, 0),
        ("valid_2.yml", {"severity": "warning"}, 0),
        ("valid_3.yml", {"severity": "warning"}, 0),
        ("valid_4.yml", {"severity": "warning"}, 0),
        ("valid_5.yml", {"severity": "warning"}, 0),
        ("valid_6.yml", {"severity": "error"}, 0),
        ("valid_7.yml", {"severity": "error"}, 0),
        ("Android.gitlab-ci.yml", {"severity": "error"}, 0),
        ("Crystal.gitlab-ci.yml", {"severity": "error"}, 0),
    ),
)
def test_valid_yaml_scripts(test_file_path, extra_args, expected):

    args = {
        "root-file": str(
            os.path.join("tests", "resources", "valid_yaml", test_file_path)
        )
    }
    args.update(extra_args)
    assert gitlab_script_check.call_ci_script_check(args) == expected
