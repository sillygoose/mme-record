"""
Gets the current version number.
If in a git repository, it is the current git tag.
Otherwise it is the one contained in the PKG-INFO file.
To use this script, simply import it in your setup.py file
and use the results of get_version() as your package version:
    from version import *
    setup(
        ...
        version=get_version(),
        ...
    )
"""
# This program is placed into the public domain.

__all__ = "get_version"

from os.path import dirname, isdir, join
from pathlib import Path
import os
import re
import subprocess

version_re = re.compile("^Version: (.+)$", re.M)


def get_version():
    """Get a version number for a tag."""
    # Assume we find no tags
    version = "unknown"

    # Save current directory and switch to the git project root directory
    current_dir = os.getcwd()
    app_path = Path(dirname(__file__))
    os.chdir(app_path)
    # print(app_path.parent)
    if isdir(join(app_path.parent, ".git")):
        # Get the version using "git describe".
        cmd = "git describe --tags --match [0-9]*".split()
        try:
            version = subprocess.check_output(cmd).decode().strip()
        except subprocess.CalledProcessError:
            pass

        # PEP 386 compatibility
        if "-" in version:
            version = ".post".join(version.split("-")[:2])

        # Don't declare a version "dirty" merely because a time stamp has
        # changed. If it is dirty, append a ".dev1" suffix to indicate a
        # development revision after the release.
        with open(os.devnull, "w") as fd_devnull:
            subprocess.call(["git", "status"], stdout=fd_devnull, stderr=fd_devnull)

        cmd = "git diff-index --name-only HEAD".split()
        dirty = ""
        try:
            dirty = subprocess.check_output(cmd).decode().strip()
        except subprocess.CalledProcessError:
            pass

        if dirty != "":
            version += ".dev"

    # Restore the original directory
    os.chdir(current_dir)
    return version


if __name__ == "__main__":
    print(__file__)
    print(get_version())
