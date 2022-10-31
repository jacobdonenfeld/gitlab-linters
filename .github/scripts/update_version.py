"""Update the version file."""
import os


def increment_version(version):
    version = version.split(".")
    version[2] = str(int(version[2]) + 1)
    return ".".join(version)


def update_manifest():
    """Update the manifest file."""
    version = "0.0.0"

    with open(f"{os.getcwd()}/pre_commit_hooks/VERSION") as version_file:
        version = version_file.read()
        version_file.close()

    next_version = increment_version(version)

    with open(f"{os.getcwd()}/pre_commit_hooks/VERSION", "w") as version_file:
        version_file.write(next_version)
        version_file.close()


update_manifest()
