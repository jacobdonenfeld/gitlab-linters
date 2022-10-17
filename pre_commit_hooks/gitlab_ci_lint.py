from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import gitlab
from git import Repo

from .shared.importer import ImportFromRootFile

# Can move this to an arg
DEBUG = False

if DEBUG:
    import logging
    import http.client as http_client

    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full-report",
        dest="report_arg",
        action="store_const",
        const="--full-report",
        default="--full-report",
    )
    parser.add_argument(
        "--short-report",
        dest="report_arg",
        action="store_const",
        const="--short-report",
    )
    parser.add_argument("--ignore", "-i", action="append")
    parser.add_argument("files", nargs="+")
    return parser


def main(argv=None):  # pylint: disable=inconsistent-return-statements
    parser = build_parser()
    parsed_args, args_rest = parser.parse_known_args(argv)
    if args_rest and len(args_rest) > 0:
        print(f"excess args: {str(args_rest)}")
        return 1
    return call_ci_check(parsed_args)


# def call_safety_check(requirements_file_paths, ignore_args, report_arg, args_rest):
# 	safety_args = []
# 	if "--disable-telemetry" in args_rest:
# 		safety_args.append("--disable-telemetry")
# 		args_rest = [arg for arg in args_rest if arg != "--disable-telemetry"]
# 	safety_args.append("check")
# 	for file_path in requirements_file_paths:
# 		safety_args += ["--file", file_path]
# 	for codes in (ignore_args or []):
# 		for code in codes.split(","):
# 			safety_args += ["--ignore", code]
# try:
# 	cli.main(safety_args + [report_arg] + args_rest, prog_name="safety")
# except SystemExit as error:
# 	return error.code
# return 1


def call_ci_check(args=None):
    # If root file is not specified, look for default location
    if args is None or "root-file" not in args:
        args = {"root-file": ".gitlab-ci.yml"}

    # Get git root directory
    git_root = Repo(".", search_parent_directories=True).working_tree_dir
    # Store cwd to return after execution
    stored_cwd = os.getcwd()
    # set working directory to base of git repo
    os.chdir(str(git_root))

    file = str(Path(args["root-file"]))

    # Path to root file
    base_path = os.path.dirname(file)
    if base_path and len(base_path) > 1:
        # If specified file doesn't exist in git root:
        os.chdir(str(base_path))

    # Filename of root file without directories
    file = os.path.basename(file)

    # # Currently only check if .gitlab-ci.yml has changed
    # 	# cmd = "git diff-index --name-only --diff-filter M HEAD | grep '^.gitlab-ci.yml$'"
    # 	# ci_changed = os.system(cmd) == 0
    # 	# if not ci_changed:
    # 	# 	return True

    # Initial logic checks:
    if not os.path.exists(file):
        print("Root CI file does not exist")
        return 1
    gl_token = os.getenv("GITLAB_TOKEN")
    gl_object = gitlab.Gitlab(private_token=os.environ["GITLAB_TOKEN"], api_version="4")

    if not gl_token:
        print("Set GITLAB_TOKEN environment variable for gitlab CI Linter")
        # print("This may work without auth")
        sys.exit(1)

    # # Currently only check if .gitlab-ci.yml has changed
    # 	# cmd = "git diff-index --name-only --diff-filter M HEAD | grep '^.gitlab-ci.yml$'"
    # 	# ci_changed = os.system(cmd) == 0
    # 	# if not ci_changed:
    # 	# 	return True

    CI_YAML, ok = ImportFromRootFile(file)
    if not ok:
        return 1

    # # Merge the dictionaries
    # fullYaml = {}
    # for file in files:
    # 	with open(file, "r") as stream:
    # 		yamlfile={}
    # 		try:
    # 			yamlfile=(yaml.safe_load(stream))
    # 			fullYaml.update(yamlfile)
    # 		except yaml.YAMLError as exc:
    # 			print(exc)

    # Write the merged dictionary to a new file

    # combinedYAML = json.dumps(fullYaml).replace('"', '\\"')
    # TODO: for now, only linting the first yaml document
    combinedYAML = json.dumps(CI_YAML[0]).replace('"', '\\"')
    # print(combinedYAML)

    # url = "https://gitlab.com/api/v4/ci/lint"
    # headers = {
    #     "content-type": "application/json",
    #     # Unsure if necessary
    #     "PRIVATE-TOKEN": os.environ["GITLAB_TOKEN"],
    # }

    try:
        lint_resp = gl_object.ci_lint.create(content={"content": combinedYAML})
        print(lint_resp)
        print(lint_resp.validate)
    except Exception as ex:
        print(ex)

    # try:
    # 	lint_result = requests.post(url, data={"content": combinedYAML}, headers=headers)
    # 	lint_result.raise_for_status()
    # except requests.exceptions.HTTPError as err:
    # 	raise SystemExit(err)
    # print(lint_result)
    # lint_result = lint_result.json()
    # if len(lint_result.errors) >= 1:
    # 	print("Errors:")
    # 	print(lint_result.errors)
    # if len(lint_result.warnings) >= 1:
    # 	print("Warnings:")
    # 	print(lint_result.warnings)
    # if not lint_result.status == "valid":
    # 	return 1

    os.chdir(stored_cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
