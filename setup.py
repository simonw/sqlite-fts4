from setuptools import setup
import os

VERSION = "1.0.1"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="sqlite-fts4",
    description="Python functions for working with SQLite FTS4 search",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Simon Willison",
    url="https://github.com/simonw/sqlite-fts4",
    project_urls={
        "Issues": "https://github.com/simonw/sqlite-fts4/issues",
        "CI": "https://github.com/simonw/sqlite-fts4/actions",
        "Changelog": "https://github.com/simonw/sqlite-fts4/releases",
    },
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["sqlite_fts4"],
    extras_require={"test": ["pytest"]},
    tests_require=["sqlite-fts4[test]"],
)
