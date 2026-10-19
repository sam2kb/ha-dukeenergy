# Duke Energy for Home Assistant

A custom integration that imports your Duke Energy electric and gas usage into
Home Assistant's Energy dashboard, with optional cost tracking.

- Hourly electric and daily gas statistics, backfilled up to three years
- Cost statistics derived from a price entity or a fixed rate, with optional
  historical backfill
- Account and meter devices with poll status, bill-cycle usage and bill amounts
- Average daily temperature per account
- Three polls a day, spread with a per-installation offset

This fork continues [hunterjm/ha-dukeenergy](https://github.com/hunterjm/ha-dukeenergy)
and is based on [crash0verride11's v2.1.4](https://github.com/crash0verride11/ha-dukeenergy).
It adds the October 2026 login fix (the extension now sends an iPhone User-Agent
to Duke's login host), config-entry diagnostics, tests in CI and its own release
pipeline. See [CREDITS.md](CREDITS.md).

> [!WARNING]
> This integration uses Duke Energy's private mobile API. It is unofficial and
> can break whenever Duke changes its app, its login or its bot protection. It
> is maintained on a best-effort basis, not as a supported product.

## Requirements

- Home Assistant 2026.2 or later
- Chrome or Edge on the machine where you sign in
- A Duke Energy account with electric and/or gas service
- HACS (recommended) or manual installation

## Install

### 1. Install the integration

Add this repository to HACS as a custom repository:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sam2kb&repository=ha-dukeenergy&category=integration)

Or, in HACS: **Custom repositories** → add
`https://github.com/sam2kb/ha-dukeenergy` → category **Integration** → install →
restart Home Assistant.

Manual install: copy `custom_components/duke_energy/` into your HA
`config/custom_components/` directory and restart.

### 2. Install the browser extension

The extension is required. Duke's login only accepts its mobile app's redirect
URI, so the browser cannot hand the authorization code back to Home Assistant on
its own. Since October 2026 Duke also rejects desktop browsers at the login page,
so the extension rewrites the User-Agent for `login.duke-energy.com` only.

1. Download `chrome-extension.zip` from the
   [latest release](https://github.com/sam2kb/ha-dukeenergy/releases/latest).
2. Extract it to a folder you will keep (Chrome loads an unpacked extension from
   that path; do not delete it afterwards).
3. Open `chrome://extensions/` (or `edge://extensions/`).
4. Enable **Developer mode**.
5. Click **Load unpacked** and select the extracted folder.

See [chrome-extension/README.md](chrome-extension/README.md) for details.

### 3. Add the integration

1. **Settings → Devices & services → Add integration → Duke Energy**.
2. Follow the login link, sign in, and complete any MFA prompt.
3. Duke redirects to a **"Not Found"** page. That is expected.
4. The extension captures the code and forwards it to Home Assistant.

## If the login fails

| What you see | Cause | What to do |
| --- | --- | --- |
| `access_denied` / "An error has occurred" instead of a code | Duke's login rejected the browser or the extension was disabled | Confirm the extension is installed and enabled, then retry. As a fallback, open DevTools (`F12`), toggle device mode (`Ctrl+Shift+M`), pick an iPhone, and sign in again |
| "Not Found" page and no code | The extension did not capture the redirect | Check the extension popup; reload the extension and retry |
| "No code was captured" | The login never completed or Duke was down | Retry later; check the extension popup for the captured URL |
| `403 Access Denied` on token exchange | Duke's API edge blocked the request | Update the integration and `aiodukeenergy-co`; if it persists, open an issue with a diagnostics dump |
| Reauthentication prompt never clears | A transient block was treated as a bad credential | Update to 2.2.0+; if it persists, download diagnostics (**Settings → Devices & services → Duke Energy → ⋮ → Download diagnostics**) and attach it to an issue |

## Cost tracking

After setup, open the integration's **Configure** dialog and pick a meter:

- **Entity price** — a sensor's long-term statistics price past usage, so
  time-of-use or seasonal rates can be a template sensor. A `number` or
  `input_number` acts as a static price.
- **Static price** — one fixed rate.
- **Do not track** — turns cost off for that meter.

**Backfill historical cost** recomputes the whole available history when you
change the price. Leave it off to price only new usage.

Cost is written as an external statistic
(`duke_energy:electric_<serial>_energy_cost`) so the Energy dashboard can track
dollars with **Use an entity tracking the total costs**.

## When data updates

Duke publishes usage with a delay. The integration polls around **09:00, 14:00
and 19:00 America/New_York**, each shifted by a per-installation offset of up
to two hours derived from the config entry ID and the date. It stops for the day
once every meter has new data.

## Statistics and entities

| Thing | Example |
| --- | --- |
| Electric consumption | `duke_energy:electric_<serial>_energy_consumption` (kWh, hourly) |
| Gas consumption | `duke_energy:gas_<serial>_energy_consumption` (CCF, daily at noon) |
| Cost | `duke_energy:<type>_<serial>_energy_cost` (USD) |
| Temperature | `duke_energy:account_<id>_temperature` (°F, daily) |

Devices: one per account (`Status`, `Last updated`, `Next scheduled update`,
bill-cycle and last-year costs, bill balance/due date/status) and one per meter
(`Last changed`, bill-cycle and last-year usage).

Statistics persist across reloads and restarts. They are only removed when you
delete the config entry.

## Known limitations

- **Unofficial API.** Duke has declined to offer automated third-party data
  access, so this integration impersonates the mobile app. When Duke changes the
  app version, user agent, client credentials or bot rules, it can break until
  someone updates the code.
- **Delayed data.** Duke's usage is roughly a day behind; there is no real-time
  reading, so the integration publishes statistics rather than live sensors.
- **Occasional reauthentication.** Refresh tokens eventually need a browser
  login. Updates reduce this by not treating CDN blocks as expired credentials,
  but it can still happen.
- **Manual fallback.** If automatic access ever stops for good, Duke's Green
  Button download can be imported with `recorder.import_statistics` to keep the
  Energy dashboard populated.

## Credits

See [CREDITS.md](CREDITS.md). MIT licensed, see [LICENSE](LICENSE).
