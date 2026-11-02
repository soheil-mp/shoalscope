# Set up a development environment

By the end of this tutorial you will have a working clone of Shoalscope with every check
passing locally, exactly as CI runs them.

## 1. Install the tools

You need three things:

- **Git**
- **[uv](https://docs.astral.sh/uv/)**, which installs Python 3.13 for you
- **[just](https://just.systems/)**, the task runner: `uv tool install rust-just`

Prefer containers? Open the repository in the devcontainer (`.devcontainer/`) in VS Code or
GitHub Codespaces; it installs the same versions and runs step 3 for you.

## 2. Clone the repository

```sh
git clone https://github.com/soheil-mp/shoalscope.git
cd shoalscope
```

## 3. Install the workspace and git hooks

```sh
just setup
```

This creates `.venv/` with the nine workspace packages and the development tools, and installs
the pre-commit hooks that run on every commit (secret scanning, linters, type checking).

## 4. Run the checks

```sh
just check
```

You should see, in order:

1. the dependency policy on `uv.lock` and on the installed packages
   (`N distributions checked, 0 violations.`),
2. Ruff lint and format checks,
3. import-linter reporting all eight contracts as `KEPT`,
4. mypy in strict mode reporting `Success`,
5. pytest passing with coverage above the 85 % floor.

## 5. Make a change

Create a branch, edit, and commit with a [Conventional Commit](https://www.conventionalcommits.org/)
message:

```sh
git switch -c docs/fix-typo
git commit -am "docs: fix a typo in the tutorial"
```

The hooks run automatically. If one fails, fix what it reports (many fix themselves) and commit
again.

## Next steps

- [Read one ping from a remote raw file](read-a-remote-ping.md) to see the ingestion idea.
- Pick an open item from the
  [roadmap](https://github.com/soheil-mp/shoalscope/blob/main/ROADMAP.md).
