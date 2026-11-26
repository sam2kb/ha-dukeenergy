# AGENTS.md

Guidance for coding agents working in this repository. README.md covers
installation for users, CONTRIBUTING.md covers the development setup and release
rules, and CHANGELOG.md records what has shipped.

## What This Is

A custom Home Assistant integration for Duke Energy, distributed through HACS.
It is a fork of [hunterjm/ha-dukeenergy](https://github.com/hunterjm/ha-dukeenergy)
0.3.1 by way of [crash0verride11's v2.1.4](https://github.com/crash0verride11/ha-dukeenergy);
the changelog dates this fork's own work from 2026-10-19.

Every call to Duke Energy goes through the `aiodukeenergy-co` package from PyPI
(import name `aiodukeenergy_co`), pinned to 1.3.2. The pin appears in four
places that have to agree: `custom_components/duke_energy/manifest.json`
`requirements`, which is what Home Assistant installs; the `dev` group in
`pyproject.toml`; `requirements-test-current.txt`; and `uv.lock`. There is no
copy of the library source in this checkout. Read the installed package at
`.venv/lib/python3.13/site-packages/aiodukeenergy_co/` when you need its
internals.

Repository layout:

- `custom_components/duke_energy/`: the integration. Filenames below are
  relative to this directory.
- `tests/`: pytest suite built on `pytest-homeassistant-custom-component`.
- `scripts/`: `develop` starts Home Assistant against `config/`, `lint` applies
  Ruff fixes, `setup` installs `requirements.txt` for the dev container.
- `.github/workflows/`: Lint, Test, Validate and Release.

## Architecture

### Two-layer auth

Duke Energy needs two token exchanges before any API call.

1. Auth0 to a Home Assistant OAuth session (`oauth.py`, `config_flow.py`).
   `LocalOAuth2ImplementationWithPkce` runs against Duke's Auth0 tenant
   (`login.duke-energy.com`) with the iOS app's client ID, the mobile app
   redirect URI, the `auth0Client` blob and an iPhone Safari user agent, all in
   `const.py`, because Duke's login rejects desktop browsers. The `id_token`
   expires in 30 minutes while the `access_token` lasts 24 hours, so
   `oauth.py:_adjust_token_expiry` sets `expires_at` from the `id_token`'s `exp`
   claim and Home Assistant refreshes before the short one lapses. A missing or
   undecodable `id_token` raises `ValueError`, which the setup path treats as an
   auth failure.

2. Auth0 `id_token` to a Duke Energy API token
   (`aiodukeenergy_co.duke_auth.AbstractDukeEnergyAuth`). Requests to
   `api-v2.cma.duke-energy.app` carry a separate bearer token obtained by
   posting the `id_token` to `/login/auth-token`. The library caches that token
   and exchanges it again when it nears expiry.

`api.py:DukeEnergyAuth` bridges the two. It subclasses `AbstractDukeEnergyAuth`
and implements `async_get_id_token()` on the HA `OAuth2Session`, turning a
rejected refresh (4xx except 408 and 429) or an unusable `id_token` into
`DukeEnergyAuthError` so the coordinator starts reauthentication, including when
that happens long after setup. Network failures and Auth0 outages stay
retryable.

The sign-in step takes a pasted redirect URL, and a pasted address from Duke's
public website is reported as a bounced sign-in rather than a malformed
callback (`config_flow.py`).

### Data flow

`coordinator.py:DukeEnergyCoordinator` owns polling and statistics.

- It uses `DataUpdateCoordinator` with `update_interval=None` and schedules
  itself. `_schedule_next_check` targets 9:00, 14:00 or 19:00
  `America/New_York` (`_DUKE_TZ`, `_BASE_TIMES_ET`) plus a per-entry, per-day
  offset of up to two hours derived from SHA-256 of the entry ID and the date
  (`_get_or_create_daily_offset`). A failed poll moves to the next slot that
  day; a successful one waits for tomorrow's first slot.
- It writes external statistics straight into the recorder with no backing
  entities. The IDs are
  `duke_energy:{service_type_lower}_{serial}_energy_consumption`,
  `duke_energy:{service_type_lower}_{serial}_energy_cost` and
  `duke_energy:account_{srcAcctId}_temperature`.
- Cost tracking is optional and configured per meter in the options flow
  (`cost_meters`), either from a price sensor entity or a flat rate. Costs are
  priced from stored consumption, never re-fetched from Duke. The options form
  can rebuild the full cost history on request (`async_rebuild_costs`), and
  `backfill_cost` is a one-shot flag that is cleared once a rebuild succeeds.
- `sensor.py` adds ordinary state sensors. Each `srcAcctId` gets an account
  device with status, last poll, next poll, bill-cycle cost, balance, due date
  and bill status. Each supported meter gets a meter device linked to its
  account with `via_device_id`, carrying last change and usage this cycle, last
  cycle and last year. Those sensors come from `get_monthly_usage()` and
  `get_billing_payment_info()` and are unrelated to the statistics.
- The status sensor walks `fetching`, `recording`, `complete` and `failed`
  (`const.py`). `recording` means rows are queued but the recorder has not
  committed them yet, so the energy dashboard cannot read them until `complete`.
- `diagnostics.py` dumps the entry and coordinator state with tokens and
  `entity_id` redacted.

### aiodukeenergy-co library

External PyPI dependency, described above. The parts that matter here:

- `dukeenergy.py`: the `DukeEnergy` client with `get_accounts()`, `get_meters()`,
  `get_energy_usage()`, `get_monthly_usage()`, `get_billing_payment_info()` and
  `get_invoices()`. Accounts and meters are cached in memory; pass
  `fresh=True` to bypass the cache.
- `duke_auth.py`: `AbstractDukeEnergyAuth`, whose `request()` injects the Duke
  bearer token and refreshes it as needed, and a standalone `DukeEnergyAuth`
  used outside Home Assistant.
- `exceptions.py`: `DukeEnergyError`, `DukeEnergyAuthError` (including
  `DukeEnergyTokenExpiredError`) and `DukeEnergyBlockedError`, which the client
  raises when a response never reached Duke's API, usually a WAF refusal with a
  non-JSON body.
- `auth0.py`: standalone Auth0 PKCE client for use outside Home Assistant.

### Statistic details

- Electric consumption: hourly intervals, `UnitOfEnergy.KILO_WATT_HOUR`,
  `StatisticMeanType.NONE`, `has_sum=True`.
- Gas consumption: daily intervals, `UnitOfVolume.CENTUM_CUBIC_FEET`,
  `StatisticMeanType.NONE`, `has_sum=True`.
- Cost: the meter's own interval (hourly for electric, daily for gas),
  `StatisticMeanType.NONE`, `has_sum=True`, unit from `hass.config.currency`.
- Temperature: one statistic per account rather than per meter, daily mean of
  the day's readings stored at noon, `UnitOfTemperature.FAHRENHEIT`,
  `StatisticMeanType.ARITHMETIC`, `has_sum=False`. A day is rewritten only when
  its stored mean differs.
- Daily rows are registered at noon, `start` plus 12 hours, because daily usage
  is better placed in the middle of its day (`_stat_start`).
- Statistics survive unload, reload and restart. They are cleared only when the
  last Duke Energy entry is removed (`__init__.py:async_remove_entry`), because
  the IDs carry no entry ownership and two logins can share a meter.

## Development

### Environment

Python 3.13 is the floor (`requires-python`, `.ruff.toml` `target-version`).
Home Assistant tests need Linux, so use WSL or the dev container on Windows.

The lockfile is the minimum profile: Home Assistant 2026.2.3 with
`pytest-homeassistant-custom-component` 0.13.316. `requirements-test-current.txt`
is the newer profile: Home Assistant 2026.10.4 on Python 3.14. CI runs both,
and the commands below match it.

### Commands

```bash
uv sync --locked --all-groups
.venv/bin/python -m pytest -q

uvx --from 'uv>=0.9.26' uv run --no-project --python 3.14.5 \
  --with-requirements requirements-test-current.txt python -m pytest -q

uvx ruff==0.15.16 check custom_components scripts
uvx ruff==0.15.16 check tests --select F
uvx ruff==0.15.16 format . --check
```

`.ruff.toml` selects all rules with the Home Assistant core ignore list and a
complexity ceiling of 25. `scripts/lint` formats and applies the safe fixes.
Python 3.14.2 broke on recorder fixtures locally while 3.14.5 passed, so keep the
current profile on 3.14.5.

To run Home Assistant by hand, use the dev container and `scripts/develop`,
which serves `config/` on port 8123 and reads the integration through
`PYTHONPATH`. Copying `custom_components/duke_energy/` into another development
instance works too; use a scratch instance when working on statistics or
removal, since those write to the recorder.

### Testing notes

`tests/conftest.py` carries most of the setup:

- `mock_api` patches `custom_components.duke_energy.DukeEnergy`, the class
  instantiated in `async_setup_entry`, plus `DukeEnergyAuth`,
  `OAuth2Session.async_ensure_token_valid` and
  `async_get_config_entry_implementation`. The coordinator receives the built
  client, so that one patch site covers the API.
- `mock_config_entry` returns a version 2 entry that has not been added to
  `hass`; tests call `add_to_hass` themselves.
- `mock_recorder` replaces `get_instance` and `async_add_external_statistics`,
  so no recorder database is needed, and `stats_store` records what the
  coordinator wrote.
- The 0.5 second batch pause is patched out so the suite stays fast.

### Translations

Keep `strings.json` and `translations/en.json` in sync, including placeholder
names. Hassfest rejects literal URLs in translation strings, so pass them
through `description_placeholders` as `callback_prefix` in `config_flow.py`
does.

## Key constraints

- All service areas are `America/New_York`. Timezone detection by service
  address would be needed if Duke ever expands.
- First import walks back at most three years, or to the meter's agreement date
  if later, in 30-day windows fetched newest first. Requests go three at a time
  (`_MAX_CONCURRENT_REQUESTS`), pausing half a second before each batch
  (`_BATCH_INTERVAL_SECONDS`) so the average rate stays near the old sequential
  walk. Incremental polls start 30 days before the last stored row so Duke's
  corrections are picked up.
- History errors are classified carefully. A 4xx other than 401, 403, 408 and
  429 means the window is outside what Duke holds, so it is treated as the end
  of the import and later ranges are skipped (`_async_get_usage_range`). A 401
  raises `ConfigEntryAuthFailed` so a rejected token starts reauthentication
  instead of truncating history. A 403 is treated as Duke's edge refusing the
  request, not a verdict on the token, so it is retried on the next schedule.
  A 5xx, 408, 429, timeout or connection error fails the poll with
  `UpdateFailed`; none of them are read as the end of history.
- Never await the recorder during setup. It does not process its queue until
  Home Assistant finishes starting, so a cost update during entry setup can
  deadlock until the bootstrap timeout cancels setup. Cost work is deferred with
  `async_at_started` (`_async_update_costs_when_started`).
- Config entry version is 2, minor version 1. A version 1 entry is migrated to
  an empty-data version 2 entry, which then asks for reauthentication.
- Version bumps: the git tag, `manifest.json`, `pyproject.toml` and the
  `ha-dukeenergy` entry in `uv.lock` must agree. Keep an empty `Unreleased`
  section at the top of the changelog.
