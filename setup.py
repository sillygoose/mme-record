#!/usr/bin/env python

"""MME Record setup."""
from pathlib import Path
from setuptools import setup

VERSION = "0.7.1"
URL = "https://github.com/sillygoose/mme-record.git"

setup(
    name="MME Record",
    version=VERSION,
    description="MME CAN bus module record utility",
    long_description=Path("README.md").read_text(),
    long_description_content_type="text/markdown",
    url=URL,
    download_url="{}/tarball/{}".format(URL, VERSION),
    author="Rick Naro",
    author_email="sillygoose@me.com",
    license="MIT",
    install_requires=[
        "python-configuration",
        "pyyaml",
        "python-can",
        "can-isotp",
        "udsoncan",
        "influxdb-client",
    ],
    zip_safe=True,
)
