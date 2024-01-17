# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
#
# Modifications Copyright OpenSearch Contributors. See
# GitHub history for details.
#
#  Licensed to Elasticsearch B.V. under one or more contributor
#  license agreements. See the NOTICE file distributed with
#  this work for additional information regarding copyright
#  ownership. Elasticsearch B.V. licenses this file to you under
#  the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
# 	http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.


from typing import Any, List

import nox

SOURCE_FILES = (
    "setup.py",
    "noxfile.py",
    "opensearchpy/",
    "test_opensearchpy/",
    "utils/",
    "samples/",
    "benchmarks/",
    "docs/",
)


@nox.session(python=["3.6", "3.7", "3.8", "3.9", "3.10", "3.11"])  # type: ignore
def test(session: Any) -> None:
    """
    runs all tests with a fresh python environment using "python setup.py test"
    :param session: current nox session
    """
    session.install(".")
    # ensure client can be imported without aiohttp
    session.run("python", "-c", "import opensearchpy\nprint(opensearchpy.OpenSearch())")
    # ensure client can be imported with aiohttp
    session.install(".[async]")
    session.run(
        "python", "-c", "import opensearchpy\nprint(opensearchpy.AsyncOpenSearch())"
    )

    session.install("-r", "dev-requirements.txt")

    session.run("python", "setup.py", "test")


@nox.session(python=["3.7"])  # type: ignore
def format(session: Any) -> None:
    """
    runs black and isort to format the files accordingly
    :param session: current nox session
    """
    session.install(".")
    session.install("black", "isort")

    session.run("isort", *SOURCE_FILES)
    session.run("black", *SOURCE_FILES)
    session.run("python", "utils/license_headers.py", "fix", *SOURCE_FILES)

    lint(session)


@nox.session(python=["3.7"])  # type: ignore
def lint(session: Any) -> None:
    """
    runs isort, black, flake8, pylint, and mypy to check the files according to each utility's function
    :param session: current nox session
    """
    session.install(
        "flake8",
        "black",
        "mypy",
        "isort",
        "pylint",
        "types-requests",
        "types-six",
        "types-simplejson",
        "types-python-dateutil",
        "types-PyYAML",
        "types-mock",
        "types-pytz",
    )

    session.run("isort", "--check", *SOURCE_FILES)
    session.run("black", "--check", *SOURCE_FILES)
    session.run("flake8", *SOURCE_FILES)

    lint_per_folder(session)

    session.run("python", "utils/license_headers.py", "check", *SOURCE_FILES)

    # Workaround to make '-r' to still work despite uninstalling aiohttp below.
    session.run("python", "-m", "pip", "install", "aiohttp")

    # Run mypy on the package and then the type examples separately for
    # the two different mypy use-cases, ourselves and our users.
    session.run("mypy", "--strict", *SOURCE_FILES)
    session.run("mypy", "--strict", "test_opensearchpy/test_types/sync_types.py")
    session.run("mypy", "--strict", "test_opensearchpy/test_types/async_types.py")

    # Make sure we don't require aiohttp to be installed for users to
    # receive type hint information from mypy.
    session.run("python", "-m", "pip", "uninstall", "--yes", "aiohttp")
    session.run("mypy", "--strict", "opensearchpy/")
    session.run("mypy", "--strict", "test_opensearchpy/test_types/sync_types.py")


def lint_per_folder(session: Any) -> None:
    """
    allows configuration of pylint rules per folder and runs a pylint command for each folder
    :param session: the current nox session
    """

    # any paths that should not be run through pylint
    exclude_path_from_linting: List[str] = []

    # all paths not referenced in override_enable will run these lints
    default_enable = [
        "line-too-long",
        "invalid-name",
        "pointless-statement",
        "unspecified-encoding",
        "missing-function-docstring",
        "missing-param-doc",
        "differing-param-doc",
    ]
    override_enable = {
        "test_opensearchpy/": [
            "line-too-long",
            # "invalid-name", lots of short functions with one or two character names
            "pointless-statement",
            "unspecified-encoding",
            "missing-param-doc",
            "differing-param-doc",
            # "missing-function-docstring", test names usually are, self describing
        ],
        "opensearchpy/": [
            "line-too-long",
            "invalid-name",
            "pointless-statement",
            "unspecified-encoding",
        ],
    }

    for source_file in SOURCE_FILES:
        if source_file in exclude_path_from_linting:
            continue

        args = [
            "--disable=all",
            "--max-line-length=240",
            "--good-names-rgxs=^[_a-z][_a-z0-9]?$",
            "--load-plugins",
            "pylint.extensions.docparams",
        ]
        if source_file in override_enable:
            args.append(f"--enable={','.join(override_enable[source_file])}")
        else:
            args.append(f"--enable={','.join(default_enable)}")
        args.append(source_file)
        session.run("pylint", *args)


@nox.session()  # type: ignore
def docs(session: Any) -> None:
    """
    builds the html documentation for the client
    :param session: current nox session
    """
    session.install(".")
    session.install(".[docs]")
    with session.chdir("docs"):
        session.run("make", "html")


@nox.session()  # type: ignore
def generate(session: Any) -> None:
    """
    generates the base API code
    :param session: current nox session
    """
    session.install("-rdev-requirements.txt")
    session.run("python", "utils/generate_api.py")
    format(session)
