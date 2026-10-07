# Contributing to rfab-proxy

Thanks for your interest in rfab-proxy. Please read this before opening a pull request: the first
rule is enforced automatically.

## Every pull request needs a GitHub issue

**A pull request that doesn't link an open issue in this repository is closed automatically.**

1. Find an existing [issue](https://github.com/dppereyra/rfab-proxy/issues), or open a new one
   describing the bug or the change you'd like to make.
2. Wait for it to be discussed and accepted before investing time in code. This is especially
   important for new features and for which common APIs rfab-proxy should support.
3. Open your pull request against `master` and link the issue in the description with a closing
   keyword, for example:

   ```text
   Closes #123
   ```

   `Fixes #123` and `Resolves #123` work too. A plain mention such as "see #123" does **not**
   count.

If your pull request was closed for having no linked issue, open or find the issue, then open a new
pull request that links it.

Security vulnerabilities are the exception: don't open a public issue. Follow
[SECURITY.md](SECURITY.md) instead.

## License

rfab-proxy is licensed under the
**GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)**. By submitting a
contribution, you agree that:

- your contribution is licensed under AGPL-3.0-or-later, and
- you wrote it yourself or otherwise have the right to submit it under that license.

## Development setup

Tool versions are pinned in `mise.toml`:

```bash
mise install    # Python 3.14 and 3.15, uv, tox and the other pinned tools
uv sync         # install rfab-proxy and its development dependencies
```

## Before you open the pull request

Run the full suite; CI runs the same thing and must pass:

```bash
tox
```

That covers:

- tests on Python 3.14 and 3.15, with **branch coverage of at least 90%**
- `flake8` (line length 99, complexity 8), `bandit`, `radon` and `vulture`
- the OpenAPI document (`openapi-spec-validator`) and the `uv.lock` consistency check

CI also runs a Trivy scan for vulnerabilities, misconfigurations and secrets.

Please also follow these conventions:

- **Write the test first.** Behaviour changes come with tests that fail without the change.
- Test files live in `tests/` and are named `tests-*.py`.
- If you add or change an endpoint, update `src/rfab_proxy/openapi.yaml` in the same pull request.
  A test fails when the routes and the specification disagree.
- Never log, trace or report credentials, tokens or other secrets.
- After changing dependencies in `pyproject.toml`, run `uv lock` and commit `uv.lock`.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/), for example
  `fix: handle an empty upstream response`.

[AGENTS.md](../AGENTS.md) has the full set of project conventions.
