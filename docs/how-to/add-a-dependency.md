# Add a dependency

Dependencies must have a permissive licence and must not be a machine-learning package
([ADR-0002](../adr/0002-deterministic-rule-based-processing.md)). This guide adds one safely.

1. Add it to the package that needs it, not to the workspace root:

    ```sh
    uv add --package shoalscope-core gsw
    ```

    Development-only tools go into the root `dev` group instead: `uv add --dev <tool>`.

2. Check the licence and scope policy:

    ```sh
    just deps
    ```

    Both checks must report `0 violations`. If a package fails with
    `licence metadata not recognised`, read its licence by hand. If it is permissive, add the
    package to `EXCEPTIONS` in `tools/check_dependencies.py` with the reason, in the same pull
    request.

3. Run `just check` and commit `pyproject.toml` and `uv.lock` together:

    ```sh
    git commit -am "build: add gsw for TEOS-10 sound speed"
    ```

4. If the dependency is a new technology rather than a library detail, propose an ADR in
   `docs/adr/`.

Renovate keeps dependencies current afterwards. It groups updates weekly, merges patch updates
of development tools automatically once CI passes, and never automerges the scientific core
(echopype, xarray, zarr, Icechunk, NumPy, SciPy, gsw), because those can change numbers.
