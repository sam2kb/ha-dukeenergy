# Changelog

All notable changes to this fork, starting with its creation on 2026-10-19.
Versions match `custom_components/duke_energy/manifest.json`.

The fork builds on [hunterjm/ha-dukeenergy](https://github.com/hunterjm/ha-dukeenergy)
0.3.1 and [crash0verride11's v2.1.4](https://github.com/crash0verride11/ha-dukeenergy).
The features that arrived with that base are listed separately in the 2.2.0
entry, so our own changes stay visible.

## [Unreleased]

Nothing yet.

## [2.3.2] - 2026-10-19

### Changed

- Simplified the sign-in dialog to four steps: set the iPhone User-Agent, open
  the sign-in link, copy the address Duke lands on, then paste it into
  **Callback URL**.
- README uses the same four steps as the dialog; per-browser detail stays in
  the troubleshooting section.

## [2.3.1] - 2026-10-19

### Fixed

- Removing one of several Duke Energy logins no longer clears the shared
  external statistics. History is cleared only when the last entry is removed,
  because statistic IDs carry no entry ownership marker.

### Changed

- Diagnostics redact user-selected price entity IDs, replace meter serials and
  internal account IDs with stable aliases (`meter_1`, ...), and report
  statistics as counts per kind instead of exporting statistic IDs.
- Pinned the API client to `aiodukeenergy-co==1.3.0` and added the
  `aiodukeenergy_co` logger to the manifest.
- CI installs from the lockfile (`--locked` / `--frozen`), the release check
  validates tag, manifest and `pyproject.toml` versions, and HACS validation no
  longer ignores brands.
- README covers Energy dashboard setup, price units, historical backfills,
  polling, updates and removal. CONTRIBUTING and the bug report template reflect
  the current tooling and allow reports when setup fails before diagnostics
  exist.
- Bundled the official Duke Energy icons and logos under
  `custom_components/duke_energy/brand/`, so HACS validation is self-contained.
- Regression coverage for multiple logins, diagnostics redaction and repeated
  gas imports against a real recorder; the suite is now 61 tests.

## [2.3.0] - 2026-10-19

### Removed

- The Chrome/Edge OAuth helper extension, its build script and its release
  asset. The OAuth callback path remains, so existing installs keep working,
  but the repo no longer ships or maintains an extension.

### Changed

- The auth dialog is now the instruction surface: per-browser User-Agent steps,
  the iPhone User-Agent, the callback copy instructions and the import wait
  notice.
- README is paste-only, with a refreshed troubleshooting table including
  "setup seems stuck".
- The release workflow only verifies the tag/manifest version (it built the
  extension before).

### Added

- `IOS_USER_AGENT` in `const.py`, exposed to the dialog as `{user_agent}`.

## [2.2.1] - 2026-10-19

### Added

- Paste-the-callback sign-in in the config flow: the dialog shows the sign-in
  link and a **Callback URL** field, so Firefox, Safari and mobile work without
  the helper.
- Validation for rejected sign-ins (`access_denied`), missing codes and stale
  state, with specific translated errors.
- Reauthentication uses the same paste form.
- Five new tests covering paste success, the callback view, rejected sign-in,
  stale state and missing code (59 total).

### Changed

- README: helper marked optional, per-browser User-Agent instructions and a
  sign-in troubleshooting table.

## [2.2.0] - 2026-10-19

First release of this fork.

### Added (fork)

- Config-entry diagnostics with token, title and identifier redaction.
- CI: pytest, scoped Ruff, hassfest and HACS validation, plus a release check
  that refuses a tag that disagrees with the manifest.
- OAuth helper extension with a rule that sends an iPhone User-Agent to
  `login.duke-energy.com` (removed in 2.3.0).
- `CREDITS.md`, preserved MIT notices, rebranded manifest/HACS metadata and
  repository description/topics.

### Inherited with the v2.1.4 base

These were already in crash0verride11's fork and are the bulk of the delta from
upstream 0.3.1:

- Gas meter support (daily statistics in CCF) and daily temperature statistics.
- Per-meter cost statistics from a price entity or a fixed rate, with optional
  historical backfill.
- Account and meter devices: status, last/next poll, bill-cycle and last-year
  usage, bill balance/due date/status.
- Three polls a day around 09:00/14:00/19:00 ET with a per-install
  deterministic offset.
- Statistics survive reloads and restarts (upstream cleared them on unload).
- CDN/WAF blocks are retried instead of being treated as a lost credential, so
  transient blocks no longer trigger reauthentication.
- 52 tests.

### Verification at release

54 tests (52 inherited + 2 diagnostics), Ruff, hassfest and HACS validation.

## Pre-fork baseline

- **hunterjm 0.3.1** (2026-09-19): Auth0/iOS OAuth, id_token expiry handling,
  electric-only hourly statistics, 12-hour polling, no test suite.
- **crash0verride11 v2.1.4**: everything listed under 2.2.0 above.

[Unreleased]: https://github.com/sam2kb/ha-dukeenergy/compare/v2.3.2...HEAD
[2.3.2]: https://github.com/sam2kb/ha-dukeenergy/releases/tag/v2.3.2
[2.3.1]: https://github.com/sam2kb/ha-dukeenergy/releases/tag/v2.3.1
[2.3.0]: https://github.com/sam2kb/ha-dukeenergy/releases/tag/v2.3.0
[2.2.1]: https://github.com/sam2kb/ha-dukeenergy/releases/tag/v2.2.1
[2.2.0]: https://github.com/sam2kb/ha-dukeenergy/releases/tag/v2.2.0
