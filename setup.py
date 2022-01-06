#!/usr/bin/env python

"""CS/ESPHome setup."""
from pathlib import Path
from setuptools import setup

VERSION = "0.4.7"
URL = "https://github.com/sillygoose/cs_esphome.git"

setup(
    name="Playback",
    version=VERSION,
    description="MME CAN bus module playback",
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
        "can-isotp",
        "python-can",
    ],
    zip_safe=True,
)
