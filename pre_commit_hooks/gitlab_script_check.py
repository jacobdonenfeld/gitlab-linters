"""Run shellcheck on script elements"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

from .shared.importer import import_from_root_file, find_root_ci_file
from .shared.debug_mode import set_debug

# Can move this to an arg
DEBUG = False

if DEBUG:
    set_debug()


def check_shellcheck_install():
    """
    Confirms shellcheck binary is installed on the system
    """
    try:
        subprocess.run(
            ["shellcheck", "--version"], stdout=subprocess.DEVNULL, check=True
        )
    except FileNotFoundError:
        print("Skipping shell linting since shellcheck is not installed.")
        sys.exit(0)


def get_shellcheck_binary():
    """
    Returns the path of the first shellcheck binary available
    if not found returns None
    """
    binary = os.environ.get("SHELLCHECK")
    if binary and len(binary) > 0:
        return binary

    return shutil.which("shellcheck")


def build_parser():
    """Construct the parser to take in command line arguments

    Returns:
        ArgumentParser: object accepting --root-file and --severity
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-file")
    parser.add_argument(
        "--severity",
        type=str,
        help="Minimum severity of errors to consider (error, warning, info, style)",
    )
    return parser


def main(argv=None):  # pylint: disable=inconsistent-return-statements
    # Parse Args
    parser = build_parser()
    parsed_args, args_rest = parser.parse_known_args(argv)
    if args_rest and len(args_rest) > 0:
        print(f"excess args: {str(args_rest)}")
        return 1
    return call_ci_script_check(parsed_args)


def call_ci_script_check(args=None):
    """

    Heft of the file. Takes in arguments, returns whether it has an error or not in the scripts.
    """
    fail = False

    check_shellcheck_install()

    # If root file is not specified, look for default location
    if args is None or "root-file" not in args:
        args = {"root-file": ".gitlab-ci.yml"}

    root_file, stored_init_working_directory = find_root_ci_file(args["root-file"])

    def validate_script(script_element, job_name: str, file_name: str) -> bool:
        """Validate a script element via shellcheck

        Args:
            script_element (object): str or list containing a full script
            job_name (str): Name of the job checking, used for printing
            file_name (str): name of the file, used for printing

        Returns:
            script_valid (bool): Whether the script was valid


        """
        split_file_name = (
            file_name.split(os.sep)[-1].rstrip("yaml").rstrip(".yml").strip(".")
        )
        if not split_file_name or not len(split_file_name) > 0:
            # Error handling in case file name becomes nothing
            split_file_name = file_name
        print(split_file_name)
        script_valid = True
        if isinstance(script_element, str):
            script_element = [script_element]
        shellcheck_cmd = [get_shellcheck_binary(), "--shell=bash"]
        if args and "severity" in args:
            shellcheck_cmd.append(f"--severity={args['severity']}")
        # Try using bash grammar via cpython:
        # https://git.savannah.gnu.org/cgit/bash.git/tree/parse.y
        temp_file_name = f"/tmp/{job_name}.{split_file_name}.sh"
        # Doesn't work with python's tempfile library
        # TODO: Add global variables exported at the beginning of each script
        with open(temp_file_name, "w", encoding="utf-8") as temp_file:
            for script_line in script_element:
                if isinstance(script_line, list):
                    print("Weird: writing sublines")
                    for script_sub_line in script_line:
                        if isinstance(script_sub_line, str):
                            temp_file.write(script_sub_line + "\n")
                        elif isinstance(script_sub_line, list):
                            for script_sub_sub_line in script_sub_line:
                                if isinstance(script_sub_sub_line, str):
                                    temp_file.write(script_sub_sub_line + "\n")
                                else:
                                    print("ISSUE COMPILING IMPORT")
                                    print("Nested lists")
                                    print(str(script_sub_line))
                                    sys.exit(1)
                else:
                    temp_file.write(script_line + "\n")
            temp_file.close()
        shellcheck = subprocess.run(shellcheck_cmd + [temp_file_name], check=False)
        if shellcheck.returncode != 0:
            msgs = []
            if shellcheck.stderr:
                msgs.append(
                    f"shellcheck exited with code {shellcheck.returncode} "
                    f"and has unexpected output on stderr:\n{shellcheck.stderr.decode().rstrip()}"
                )
            if shellcheck.stdout:
                msgs.append(
                    f"shellcheck found issues:\n{shellcheck.stdout.decode().rstrip()}"
                )
            if not msgs:
                msgs.append(
                    f"shellcheck exited with code {shellcheck.returncode} "
                    f"and has no output on stdout or stderr."
                )
            print("\n".join(msgs))
            print("\n")
            script_valid = False

        # remove temporary file used for checking the script
        os.remove(temp_file_name)

        if not script_valid:
            print("Job (above): " + job_name)
            print("File: " + file_name)
            print("\n")
        return script_valid

    ci_yaml, completed_successfully = import_from_root_file(root_file)
    if not completed_successfully:
        fail = True

    # Validate the scripts
    for yaml_dict, yaml_file_name in ci_yaml:
        # Check for global scripts
        valid_script_keys = ["before_script", "script", "after_script"]
        for valid_script_key in valid_script_keys:
            if valid_script_key in yaml_dict:
                valid = validate_script(
                    yaml_dict[valid_script_key], "global", yaml_file_name
                )
                if not valid:
                    fail = True
        # Check for job level scripts
        for key, value in yaml_dict.items():
            # key is the potential job name
            if isinstance(value, dict):
                valid_script_keys = ["before_script", "script", "after_script"]
                for valid_script_key in valid_script_keys:
                    if valid_script_key in value:
                        valid = validate_script(
                            value[valid_script_key], key, yaml_file_name
                        )
                        if not valid:
                            fail = True
    # If we changed cwd, return it back
    os.chdir(stored_init_working_directory)

    # Exit codes
    if fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
