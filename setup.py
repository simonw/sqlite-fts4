from setuptools import setup
import os

VERSION = "0.2"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="sqlite-fts4-rank",
    description="Python ranking functions for SQLite FTS4 search",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Simon Willison",
    url="https://github.com/simonw/sqlite-fts4-rank",
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["sqlite_fts4_rank"],
    setup_requires=["pytest-runner"],
    extras_require={"test": ["pytest==4.0.2"]},
)
