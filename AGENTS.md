# AGENTS.md

Working agreements for coding agents in the `rfab-proxy` repository.
This file records decisions that are **not** derivable from the code itself.
Add to it whenever a new standing preference is given.

## Ground rule: no work without a tracked issue

**No active work happens without an issue in Linear.** The plan lives in the
Linear project **rfab-proxy** (team *Personal*), split into milestones. Before
writing code, editing config, or opening a PR, there must be an issue covering
it. Work that arrives mid-task and isn't covered by the issue in hand gets its
**own issue** first; never fold it silently into an unrelated one.

- **Linear stays out of git and GitHub.** This is a personal project: branch
  names, commit messages, PR titles and PR bodies carry no Linear IDs or
  references (`DPP-<n>`). Link the PR from the Linear ticket instead.
- Move an issue to `Done` only once its PR is merged.

### Outside contributions

- **Pull requests from anyone else must link an open GitHub issue** with a
  closing keyword (`Closes #123`). `.github/workflows/require-linked-issue.yml`
  closes any that don't, with a comment pointing at `.github/CONTRIBUTING.md`.
  PRs from `dppereyra` and Dependabot are exempt, since that work is tracked in
  Linear.

## Identity and accounts

- This is a **personal** project. Commits are authored as
  `DPPereyra <dppereyra@gmail.com>`; don't override the git identity.
- The `gh` CLI must be authenticated as **`dppereyra`**. Several accounts are
  authenticated on this machine and the active one is global state, so verify
  before any API call:

  ```bash
  gh api user --jq .login                                  # who is active
  gh auth switch --hostname github.com --user dppereyra    # make it dppereyra
  ```

  `git push` uses SSH and is independent of the `gh` token, so a push can
  succeed while `gh` API calls (PR creation, branch protection) fail.
- Before committing or pushing, check whether work is in flight under another
  account, and pause if so.

## Branches and pull requests

- **One branch and one PR per Linear issue**, merged into `master`.
- **Branch names are `<type>/<short-slug>`**, where the type is the
  Conventional Commit type (`feat/`, `fix/`, `docs/`, `ci/`, `build/`,
  `chore/`), for example `docs/contributing-issue-gate`. Don't use the
  `feature/dpp-<n>-...` names Linear generates; ticket IDs in branch names are
  a work convention, not this project's.
- **Head branches are deleted automatically when a PR merges** (repository
  setting). GitHub then retargets PRs stacked on the merged branch, and
  `git town sync` removes the local copy.
- **Stacked PRs are managed with [git-town](https://www.git-town.com/)**, never
  by hand with `git switch -c` and `gh pr edit --base`. The repository is
  already configured (`main = master`, GitHub through the `gh` connector):

  ```bash
  git town hack <branch>      # new branch off master
  git town append <branch>    # new branch stacked on the current one
  git town sync               # keep the stack up to date
  git town propose            # open the PR against the branch's parent
  git town branch             # show the stack
  ```

  Deleting a merged branch by hand closes any PR based on it; let GitHub's
  automatic deletion and git-town handle it. git-town needs a one-time
  `git town init` in a real terminal before its commands run unattended.
- **Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)**
  (`feat:`, `fix:`, `build:`, `ci:`, `test:`, `docs:`, `chore:`, with an
  optional scope). The release pipeline will derive versions from them.
- Versions are tag-derived (hatch-vcs); never add a version file or bump a
  version by hand.

## Toolchain

- **mise** pins every tool (`mise.toml`): Python 3.14 and 3.15, uv, tox with
  tox-uv, Trivy, Helm and MkDocs. Run `mise install` after cloning.
  `mise.toml` is the single source of truth for versions, and CI reads the
  Python matrix and the uv version from it (`mise run ci:versions`).
- **tox is the canonical runner**, and CI runs tox rather than the tools
  directly. Run everything with `tox`, or one env with `tox -e lint`.
  The Hatch scripts and the mise tasks (`test`, `lint`, `security`, `serve`)
  are local shortcuts that mirror tox.
- Config lives in `tox.ini` (tox envs, pytest, coverage, flake8) and
  `pyproject.toml` (packaging, dependencies, Hatch envs).
- To add or drop a Python version, change `mise.toml` and add the matching env
  to `tox.ini`; the CI matrix follows automatically.

## Quality bars

These are enforced, not aspirational. CI fails on any of them:

- **Development is test-driven.** Write the failing test first, then the code
  that makes it pass. A PR that adds behaviour without a test written before it
  is not done.
- **Coverage must be at least 90%** (`fail_under = 90`, branch coverage on).
  Changing the bar needs its own issue.
- `flake8`: max line length 99, max complexity 8.
- `bandit`, `radon`, and `vulture --min-confidence 75` must all pass clean.
- **Trivy must be clean** (`vuln`, `misconfig`, `secret`). There is no
  `.trivyignore`; a finding is fixed or explicitly accepted in its issue, never
  silenced in the repo.
- The OpenAPI document must pass `openapi-spec-validator` (`tox -e openapi`).
- Supported Python is **3.14 and 3.15** (`requires-python = ">=3.14"`). Both
  block the `CI` gate; 3.15 installs as a pre-release until 3.15.0 ships.

## Layout and conventions

- `src/rfab_proxy/` holds the package and `tests/` the test suite. Both folders
  are required. `scripts/` is repository tooling outside the package.
- Test files are named `tests-*.py` (not `*_test.py`), per `python_files` in
  `tox.ini`.
- The web framework is **Falcon in ASGI mode** (`falcon.asgi.App`), served by
  **uvicorn**. The upstream HTTP client is **httpx**.
- `create_app()` builds the plain Falcon app; tests use it with
  `falcon.testing`. `create_asgi_app()` wraps it in OpenTelemetry and is what
  uvicorn serves (`rfab-proxy` / `python -m rfab_proxy`). Test the instrumented
  app through `httpx.ASGITransport`, because `falcon.testing`'s ASGI scope
  breaks the OpenTelemetry middleware.
- Configuration comes only from environment variables, read in
  `rfab_proxy.config.Settings` and validated at startup: `RFAB_HOST`
  (default `127.0.0.1`; containers set `0.0.0.0`), `RFAB_PORT`,
  `RFAB_LOG_LEVEL`, `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_SAMPLE_RATE`,
  and the standard `OTEL_*` variables.
- Probes: `GET /healthz` (liveness) and `GET /readyz` (readiness, 503 when a
  check fails).
- Logging goes through stdlib `logging` as JSON lines. Errors return Falcon's
  JSON error body; unexpected exceptions become a bare 500 and never expose
  their message.
- **The OpenAPI spec is written first.** `src/rfab_proxy/openapi.yaml`
  (OpenAPI 3.1) is the source of truth and is served at `/openapi.json`. Adding
  or changing a route means updating the spec in the same PR; a test fails when
  routes and spec drift apart.

## Observability and credentials

- **OpenTelemetry owns traces and metrics; Sentry only reports errors.** Sentry
  tracing stays off so nothing is traced twice. Both are inert unless
  configured (`OTEL_EXPORTER_OTLP_ENDPOINT`, `SENTRY_DSN`), so local runs and
  tests send nothing.
- **A proxy's URLs and headers can carry upstream credentials.** Keep them out
  of every sink:
  - query-string values are redacted (`rfab_proxy.redaction`) in span URLs and
    uvicorn access logs, and httpx request logging stays at WARNING
  - request headers are never recorded as span attributes
  - Sentry events have no PII and no frame locals, and credential headers and
    cookies are scrubbed before they're sent

  Any new log line, span attribute or error report must follow the same rules.
- Tests run with every `RFAB_*`, `SENTRY_*` and `OTEL_*` variable cleared
  (`tests/conftest.py`), so a value in the developer's shell can't reach a
  live service.

## Security defaults

- **When a security-related behaviour is undecided, the more secure and less
  intrusive option is the default.** Loosening a default is a deliberate change
  with its own issue.

## CI

- `.github/workflows/ci.yml` triggers on `workflow_dispatch`, on
  `pull_request` to `master` (`opened`, `synchronize`, `reopened`), and on
  `push` to `master`. PRs based on another branch (a stack) only get CI once
  they target `master`.
- The aggregate **`CI`** job is the single status check for branch protection;
  matrix job names change whenever the matrix does, and this one doesn't. If
  you add a job, wire it into the `ci` job's `needs`.
- Actions are pinned by commit SHA, checkouts don't persist credentials, and
  `actionlint` and `zizmor` should both be clean after any workflow change.
- `fetch-depth: 0` is required wherever the package is built, because hatch-vcs
  derives the version from git tags.
- SonarCloud analysis runs once the `SONAR_TOKEN` secret is set, and is skipped
  with a notice until then.

## Dependencies

- **`uv.lock` is the source of truth for installed versions.** tox installs from
  it (`runner = uv-venv-lock-runner`), and `tox -e lock` fails when it drifts
  from `pyproject.toml`. After changing a dependency, run `uv lock` and commit
  the result.
- Check a new dependency's maintenance, licence and security posture before
  adding it, and note the evaluation in the PR.
- **Dependabot** (`.github/dependabot.yml`) covers `uv` and `github-actions`
  weekly on Friday, with a 7-day cooldown. Dev dependencies and actions are
  grouped.
- A Dependabot PR is merged only after the updated dependency set has been
  installed and the full quality suite run in a **throwaway container** (one
  per supported Python), not only on the basis of a green CI run.

## License

- The project is licensed **AGPL-3.0-or-later** (`LICENSE`, `pyproject.toml`,
  OpenAPI `info.license`). Don't introduce any other license reference.

## Agent instructions

- **This file is the only place for agent-facing instructions.** Don't add
  `CLAUDE.md`, `.cursorrules`, or any other tool-specific instruction file;
  point tools that expect one at `AGENTS.md` instead.
