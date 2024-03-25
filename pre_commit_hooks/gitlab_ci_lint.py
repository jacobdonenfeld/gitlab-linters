"""Run gitlab's lint api on yaml files"""

from __future__ import annotations

import argparse
import json
import os
import sys

import gitlab

from .shared.importer import import_from_root_file, find_root_ci_file
from .shared.debug_mode import set_debug

# Can move this to an arg
DEBUG = False

if DEBUG:
    set_debug()


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

    root_file_name = args["root-file"]

    root_file, stored_init_working_directory = find_root_ci_file(root_file_name)

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

    ci_yaml, returned_successfully = import_from_root_file(root_file)
    if not returned_successfully:
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

    # combined_yaml = json.dumps(fullYaml).replace('"', '\\"')
    # TODO: for now, only linting the first yaml document
    combined_yaml = json.dumps(ci_yaml[0]).replace('"', '\\"')
    # print(combined_yaml)

    # url = "https://gitlab.com/api/v4/ci/lint"
    # headers = {
    #     "content-type": "application/json",
    #     # Unsure if necessary
    #     "PRIVATE-TOKEN": os.environ["GITLAB_TOKEN"],
    # }

    try:
        lint_resp = gl_object.ci_lint.create(content={"content": combined_yaml})
        print(lint_resp)
        print(lint_resp.validate)
    except Exception as ex:
        print(ex)

    # try:
    # 	lint_result = requests.post(url, data={"content": combined_yaml}, headers=headers)
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

    os.chdir(stored_init_working_directory)
    return 0


if __name__ == "__main__":
    sys.exit(main())
