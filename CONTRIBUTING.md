# Contributing

Report bugs and suggest changes through [GitHub issues](https://github.com/sam2kb/ha-dukeenergy/issues).
For a bug, include the Home Assistant and integration versions, steps to
reproduce, expected behavior and the actual result. Attach diagnostics when
available and review logs for personal information, tokens and callback URLs
before posting. See the [README](README.md#reporting-a-problem).

## Development setup

Use Python 3.13 and [uv](https://docs.astral.sh/uv/). Home Assistant tests run on
Linux; on Windows, use WSL or the included VS Code development container.

```bash
uv sync --locked --all-groups
uv run --frozen pytest -q
```

The lockfile selects the test dependencies used by CI. To run the same lint and
format checks as CI:

```bash
uvx ruff==0.15.16 check custom_components scripts
uvx ruff==0.15.16 check tests --select F
uvx ruff==0.15.16 format . --check
```

With Ruff installed, `scripts/lint` applies formatting and automatic fixes.

## Running Home Assistant locally

Open the repository in the included VS Code development container. Its setup
installs `requirements.txt`; run `scripts/develop` to start Home Assistant using
the configuration in `config/` on port 8123. Run `uv sync` separately for tests.

You can also copy or symlink `custom_components/duke_energy/` into a development
Home Assistant installation's `custom_components/` directory and restart it.
Use a test installation when working on statistics or removal behavior.

## Pull requests

1. Create a branch from `main` in your fork.
2. Keep changes focused and update documentation when behavior changes.
3. Add regression coverage for changes to authentication or statistics.
4. Run the tests and lint checks above, then open a pull request with the
   problem, resulting behavior and validation results.

Keep `strings.json` and `translations/en.json` in sync when changing UI text.
The API dependency in `manifest.json` must match the version tested in
`pyproject.toml`; update `uv.lock` when changing dependencies. Hassfest and HACS
validation run in GitHub Actions.

For a release, the Git tag (with an optional `v` prefix), manifest version and
project version must match. Run the Release workflow manually to check project
and manifest versions before publishing a GitHub release. HACS uses GitHub
release tags; no ZIP upload is required by this repository's configuration.

## License and credits

Contributions use the [MIT license](LICENSE). Preserve existing copyright
notices and credit upstream work; see [CREDITS.md](CREDITS.md).
