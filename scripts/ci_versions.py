"""Print the CI version matrix from mise.toml as JSON.

mise.toml is the single source of truth for tool versions; CI reads the
Python test matrix and the uv version from here instead of repeating them.
"""

import json
import sys
import tomllib
from pathlib import Path


def _major_minor(version):
    major, minor = version.split(".")[:2]
    return f"{major}.{''.join(c for c in minor if c.isdigit())}"


def versions(path):
    with Path(path).open("rb") as handle:
        tools = tomllib.load(handle)["tools"]

    pythons = tools["python"]
    if isinstance(pythons, str):
        pythons = [pythons]

    pythons = [_major_minor(python) for python in pythons]
    return {
        "python": [
            {"python": python, "toxenv": "py" + python.replace(".", "")}
            for python in pythons
        ],
        "uv": tools["uv"],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else "mise.toml"
    print(json.dumps(versions(path)))


if __name__ == "__main__":
    main()
