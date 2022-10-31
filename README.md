# Gitlab-lint-hooks

<p align="center"> A command line tool and pre-commit hooks for running static analysis on gitlab-ci configuration.</p>

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Build Status](https://github.com/jacobdonenfeld/gitlab-linters/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/jacobdonenfeld/gitlab-lint-hooks/actions/workflows/publish-to-pypi.yml)
[![Tests](https://github.com/jacobdonenfeld/gitlab-linters/actions/workflows/ci.yml/badge.svg)](https://github.com/jacobdonenfeld/gitlab-lint-hooks/actions/workflows/ci.yml)

## Install
**Option 1:** Build and download from repository:
```
pip install git+https://github.com/jacobdonenfeld/gitlab-linters#0.0.1
```
**Option 2:** (In progress)

install from pypi

## Quick Start

Run [shellcheck](https://github.com/koalaman/shellcheck) on all scripts:

- From a git repository with a .gitlab-ci.yaml file at the top level of the project:
```
gitlab-ci-lint
```