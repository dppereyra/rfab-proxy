"""The OpenAPI document, generated from the Falcon routes.

Routes are documented with ``@api.validate(...)``: the docstring becomes the
summary and description, and the Pydantic models in ``rfab_proxy.schemas``
become the schemas. Strict mode leaves undecorated routes out, and a test fails
when any exposed route is missing from the document.

Export the document with ``python -m rfab_proxy.openapi [--output FILE]``.
"""

import argparse
import json
import sys

from spectree import SpecTree
from spectree.config import License

from rfab_proxy import __version__

DOCS_PATH = "docs"

api = SpecTree(
    "falcon-asgi",
    title="rfab-proxy",
    version=__version__,
    description="Use rfab.ai from local tools through the common AI APIs they already speak.",
    license=License(
        name="AGPL-3.0-or-later", url="https://www.gnu.org/licenses/agpl-3.0.html"
    ),
    path=DOCS_PATH,
    mode="strict",
)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export the rfab-proxy OpenAPI document.")
    parser.add_argument("--output", help="write to this file instead of stdout")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    # Under `python -m` this file runs as __main__, a second copy of the
    # module; the routes register with the canonical rfab_proxy.openapi.api.
    from rfab_proxy import openapi
    from rfab_proxy.app import create_app
    from rfab_proxy.config import Settings

    create_app(Settings())
    document = json.dumps(openapi.api.spec, indent=2) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(document)
    else:
        sys.stdout.write(document)


if __name__ == "__main__":  # pragma: no cover
    main()
