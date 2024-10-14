"""Update the version file."""

import os
import sys


def update_manifest():
    """Update the manifest file."""
    version = "0.0.0"
    for index, value in enumerate(sys.argv):
        if value in ["--version", "-V"]:
            version = sys.argv[index + 1]

    with open(f"{os.getcwd()}/pre_commit_hooks/VERSION", "w") as version_file:
        version_file.write(version)
        version_file.close()


update_manifest()
