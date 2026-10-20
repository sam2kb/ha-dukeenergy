# Changelog

Release history for this fork, starting on 2026-10-19. Versions match
`custom_components/duke_energy/manifest.json`.

This fork builds on [hunterjm/ha-dukeenergy](https://github.com/hunterjm/ha-dukeenergy)
0.3.1 and [crash0verride11's v2.1.4](https://github.com/crash0verride11/ha-dukeenergy).
The 2.2.0 entry credits the features inherited from that base.

## [Unreleased]

## [2.3.4] - 2026-10-20

- Retry setup after OAuth timeouts and temporary HTTP 408/429 responses. Rejected token refreshes during normal polling now start Home Assistant reauthentication.
- Retry interrupted historical usage requests after network failures, rate limits and server errors instead of treating partial history as a completed import. Preserve the existing handling of other 4xx history-boundary responses.
- Resume consumption totals from the last recorded sum when Duke's returned data no longer overlaps stored history.
- Cancel the custom poll timer during coordinator shutdown and prevent a late update from scheduling it again.
- Reject non-finite current or static prices before using them for cost tracking.
- Test against both the locked HA 2026.2 environment and pinned HA 2026.10.2, including native recorder imports and shutdown cleanup. Keep entity IDs, sign-in steps and existing history intact.

## [2.3.3] - 2026-10-19

### Changed

- Clarified release notes, upstream attribution, polling and diagnostic details.
- Consolidated the original fork research into
  [maintenance notes](docs/upstream-research.md), preserving the full triage
  report in Git history.
- Updated the hassfest action pin to
  `d05c25388490cd662baef8495e1bc764c3386153`. The hassfest action files are
  unchanged from the previous pin.

## [2.3.2] - 2026-10-19

### Changed

- Simplified the sign-in instructions in the README and setup dialog: change
  the User-Agent to the supplied iPhone value, open the sign-in link and log in,
  copy the redirected tab's address, then paste it into **Callback URL**.
- Removed the browser-specific walkthroughs from the setup instructions.

## [2.3.1] - 2026-10-19

### Fixed

- Removing one Duke Energy login now preserves statistics while another login
  remains configured. Removing the final login still clears all Duke Energy
  statistics. Statistics cannot be assigned to individual logins because their
  IDs do not record which entry created them.

### Changed

- Diagnostics redact price-entity IDs and replace meter serials with local labels
  such as `meter_1`. Statistics are reported as counts by type instead of
  statistic IDs, which contain internal account IDs or meter serials.
- Pinned the API client to `aiodukeenergy-co==1.3.0`, matching the tested version.
  Added the `aiodukeenergy_co` logger so integration debug logging includes the
  API client.
- CI uses the dependency lockfile (`--locked` / `--frozen`). Release checks now
  compare the tag, manifest and `pyproject.toml` versions; manual runs check the
  project and manifest versions.
- Bundled the official Duke Energy icons and logos in
  `custom_components/duke_energy/brand/` and enabled HACS brand validation.
- Expanded the README with Energy dashboard setup, price units, cost backfills,
  polling, updates and removal behavior. Updated CONTRIBUTING and the bug-report
  form, including reports where setup fails before diagnostics are available.
- Aligned `scripts/lint` with CI's separate lint rules for integration code and
  tests.

### Validation

- Added regression coverage for multiple logins, diagnostic redaction and
  repeated gas imports using a real Home Assistant recorder.
- All 61 tests, Ruff, hassfest and HACS validation passed.

## [2.3.0] - 2026-10-19

### Changed

- Made pasted callback URLs the documented sign-in method. The setup dialog
  includes sign-in instructions, the iPhone User-Agent and an initial-import
  notice.
- Updated README troubleshooting to explain the callback page and the wait
  during the first usage import.
- Reduced the release workflow to version verification after removing the
  extension build and upload steps.

### Added

- A shared `IOS_USER_AGENT` constant in `const.py`, passed to the setup dialog
  through the `{user_agent}` placeholder.

### Removed

- The Chrome/Edge OAuth helper extension, its build script and release asset.
  Existing OAuth callback handling was retained.

## [2.2.1] - 2026-10-19

### Added

- A **Callback URL** field beside the sign-in link. Users can paste the address
  returned by Duke in Firefox, Safari or a mobile browser.
- Specific errors for rejected sign-ins (`access_denied`), missing authorization
  codes and callback URLs from a different sign-in attempt.
- The same callback form for reauthentication.
- Five tests for pasted callbacks, callback-view handling, rejected sign-ins,
  stale state and missing codes, bringing the suite to 59 tests.

### Changed

- Updated the README with User-Agent guidance and sign-in troubleshooting.
  At this release, the OAuth helper was optional; it was removed in 2.3.0.

## [2.2.0] - 2026-10-19

First release of this fork.

### Added in this fork

- Downloadable config-entry diagnostics with token, title and identifier
  redaction.
- Automated pytest and release-version checks, plus updates to the Ruff,
  hassfest and HACS validation workflows.
- An OAuth helper that sent an iPhone User-Agent to `login.duke-energy.com`.
  This helper was removed in 2.3.0.
- `CREDITS.md`, preserved MIT copyright notices, and updated repository,
  manifest and HACS metadata.

### Inherited from crash0verride11 v2.1.4

These features and fixes were already in the v2.1.4 base and account for most
of the changes from hunterjm's 0.3.1 release:

- Daily gas consumption statistics in CCF and daily temperature statistics.
- Per-meter cost statistics using a price entity or a fixed rate, with optional
  historical backfills.
- Account and meter devices with update status, last and next poll times,
  bill-cycle and prior-year usage and costs, bill balance, due date and status.
- Up to three scheduled checks per day around 09:00, 14:00 and 19:00 Eastern,
  shifted by a per-installation daily offset of up to two hours. Remaining
  checks are skipped once every supported meter has yesterday's data.
- Statistics survive reloads and restarts. The original integration cleared
  them when it unloaded.
- Separate handling for temporary Duke API CDN/WAF blocks and rejected
  credentials. Blocked requests fail the poll and retry on the next schedule,
  reducing unnecessary reauthentication prompts.
- An existing suite of 52 tests.

### Validation

- All 54 tests passed: 52 inherited tests and two diagnostics tests.
- Ruff, hassfest and HACS validation passed.

## Earlier versions

- **hunterjm 0.3.1** (2026-09-19): Auth0/iOS OAuth, `id_token` expiry handling,
  hourly electricity statistics and 12-hour polling. This release had no test
  suite.
- **crash0verride11 v2.1.4**: the gas, cost, device, polling, statistics-retention
  and authentication improvements credited in the 2.2.0 entry above.

[Unreleased]: https://github.com/sam2kb/ha-dukeenergy/compare/v2.3.4...HEAD
[2.3.4]: https://github.com/sam2kb/ha-dukeenergy/releases/tag/v2.3.4
[2.3.3]: https://github.com/sam2kb/ha-dukeenergy/releases/tag/v2.3.3
[2.3.2]: https://github.com/sam2kb/ha-dukeenergy/releases/tag/v2.3.2
[2.3.1]: https://github.com/sam2kb/ha-dukeenergy/releases/tag/v2.3.1
[2.3.0]: https://github.com/sam2kb/ha-dukeenergy/releases/tag/v2.3.0
[2.2.1]: https://github.com/sam2kb/ha-dukeenergy/releases/tag/v2.2.1
[2.2.0]: https://github.com/sam2kb/ha-dukeenergy/releases/tag/v2.2.0
