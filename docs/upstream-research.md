# Upstream research and maintenance notes

This reference retains the findings used to choose the fork's base on
2026-10-19. The original
[triage report](https://github.com/sam2kb/ha-dukeenergy/blob/12e834bb326659fff6c1f9c80f379b5e8629633e/docs/upstream-triage.md)
is preserved in Git history. Its repository counts, issue statuses and proposed
setup approach describe that earlier snapshot.

For current setup, use the [README](../README.md#2-sign-in). The
[changelog](../CHANGELOG.md) records what shipped, and
[CREDITS.md](../CREDITS.md) identifies the upstream contributors.

## Why this base was chosen

The fork started from crash0verride11's v2.1.4 at `5a517d3`, with the
`aiodukeenergy-co` client. That base already included gas and temperature
statistics, per-meter costs, account and meter devices, scheduled polling,
statistics retention across reloads, and separate handling of blocked requests
and rejected credentials. Its 52 tests passed against Home Assistant 2026.2.3
during the original review.

The later callback form, diagnostics, multiple-login history protection,
documentation and CI changes are described in the changelog. Preserve this
distinction when attributing features or comparing forks.

## Authentication failures occur at different stages

A failed login can come from the browser authorization step, the Auth0 token
exchange, or the exchange of an Auth0 ID token for a Duke API token. Identify
which endpoint failed before changing authentication behavior.

- The browser sign-in requires the mobile User-Agent shown in setup. The
  integration accepts the complete redirected URL through **Callback URL**.
- Duke API CDN/WAF refusals are represented by `DukeEnergyBlockedError` and
  translated to a failed poll (`UpdateFailed`), allowing a scheduled retry.
- Rejected Duke credentials use `DukeEnergyAuthError` and trigger
  reauthentication (`ConfigEntryAuthFailed`).
- Network failures while establishing the OAuth session defer setup through
  `ConfigEntryNotReady`.

The original review used source code and community reports, without a live
Duke account. Recheck the failing stage if Duke changes its login or API behavior.

## Statistics and costs

Keep the `duke_energy` domain and existing statistic IDs when moving work
between forks. Reloading or restarting must preserve statistics. Removing one
login must also preserve them while another login remains; deleting the final
login clears the integration's external statistics.

Cost statistics are calculated from a price entity or a static rate. They are
usage estimates; fixed charges and taxes are not added automatically. An
explicit cost backfill reprices stored consumption without changing the
consumption history.

## Questions that still need evidence

- Version 2.3.4 retries historical requests after timeouts, connection failures,
  HTTP 408/429 and server errors. Other 4xx responses still end pagination.
  Establish how Duke signals its historical data limit before changing that
  remaining behavior.
- The original research did not establish support for separate Piedmont Natural
  Gas account systems. Validate the account and API coverage before making
  broader gas-service claims.
- Treat Duke API and Home Assistant changes as separate compatibility concerns.
  Review client updates against the pinned dependency and run the existing
  tests before changing either.

## October 2026 account discovery change

[Issue #5](https://github.com/sam2kb/ha-dukeenergy/issues/5) reports successful
OAuth and token exchange followed by a 403 from `account-list`. The
[upstream patch by @b-v-co](https://github.com/hunterjm/aiodukeenergy/pull/25)
uses `account/list` and normalizes the changed account response. Its reported
live check covers one residential electric account; this fork also tests
synthetic gas and multi-account responses.

Version 2.3.5 used a local account-discovery override because the pinned
`aiodukeenergy-co` 1.3.0 still called the retired route. The next update pins
1.3.2 and removes that override. Transport regressions cover the library's
source-ID preservation, missing/empty field defaults, multiple accounts and
cache preservation after a failed refresh. When both BP-number spellings
are populated, the library prefers the current `BP` spelling, with the legacy
`Bp` spelling as a fallback.

## October 2026 client and integration updates

The [1.3.2 client release](https://github.com/crash0verride11/aiodukeenergy/releases/tag/v1.3.2)
also moves monthly usage from `account/usage/monthly` to
`account/usage/comparison`, using `accountNumber` instead of source IDs in
that request. The response format is unchanged. Both electric and gas
transport tests check the new route, account number and service units.

[crash0verride11's rollover fix](https://github.com/crash0verride11/ha-dukeenergy/commit/f316ba0b7979236d8b0ba3f97fde57e2d0d4b6d9)
is also included: on the day after a billing cycle ends, use that completed
cycle's start until the new cycle has a day of usage. This keeps the summary
start on or before its cutoff of yesterday.

The fork's resilience and diagnostics commits backport changes already in
this integration. Its manual sign-in and browser-extension changes serve its
two sign-in paths; this fork keeps the existing callback form. Those changes
do not need to be copied here.
