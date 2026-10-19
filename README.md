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
It adds the October 2026 login fixes (an optional Chrome/Edge helper and a
paste-the-callback flow that works in any browser), config-entry diagnostics,
tests in CI and its own release pipeline. See [CREDITS.md](CREDITS.md).

> [!WARNING]
> This integration uses Duke Energy's private mobile API. It is unofficial and
> can break whenever Duke changes its app, its login or its bot protection. It
> is maintained on a best-effort basis, not as a supported product.

## Requirements

- Home Assistant 2026.2 or later
- Any modern browser. Chrome/Edge can use the helper for a fully automatic
  handoff; other browsers paste the callback URL (see below)
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

### 2. Sign-in helper (optional)

Duke's login only accepts its mobile app's redirect URI, so the browser cannot
hand the authorization code back to Home Assistant by itself. There are two ways
to bridge that gap:

- **Automatic (Chrome/Edge).** Install the helper from the
  [latest release](https://github.com/sam2kb/ha-dukeenergy/releases/latest):
  1. Download `chrome-extension.zip` and extract it to a folder you will keep
     (Chrome loads an unpacked extension from that path).
  2. Open `chrome://extensions/` (or `edge://extensions/`).
  3. Enable **Developer mode**, click **Load unpacked**, and select the folder.

  The helper forwards the code and rewrites the User-Agent for
  `login.duke-energy.com` only. See
  [chrome-extension/README.md](chrome-extension/README.md).

- **Manual (any browser).** Skip the helper and paste the callback URL into
  Home Assistant. See
  [Sign in without the extension](#sign-in-without-the-extension).

### 3. Add the integration

1. **Settings → Devices & services → Add integration → Duke Energy**.
2. Open the sign-in link. With the helper installed, the flow finishes by itself
   after you sign in. Otherwise Duke sends you to a **"Not Found"** page: copy
   the full address from the address bar and paste it into the **Callback URL**
   field.
3. Complete any MFA prompt in the same browser tab.

## Sign in without the extension

The config flow accepts the callback URL directly, so any browser works:

1. Make Duke's login see a phone. Duke rejects desktop browsers after the
   password step:
   - **Firefox:** `about:config` → add a **String** named
     `general.useragent.override` with the iPhone value below. Firefox has no
     per-site override, so reset the pref when you are done.
   - **Safari:** enable the Develop menu, then
     **Develop → User Agent → Safari — iOS 18 — iPhone**.
   - **Chrome/Edge:** DevTools (`F12`) → device toolbar (`Ctrl+Shift+M`) →
     iPhone.
2. Start the integration (or reauthentication) and open the sign-in link in that
   tab. Sign in.
3. Duke lands on a "Not Found" page whose address ends in `?code=…&state=…`.
4. Copy the **entire** address and paste it into **Callback URL**.
5. If the page says `access_denied`, the browser still looked like a desktop;
   repeat from step 1 with a fresh sign-in link.

```
Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1
```

## If the login fails

| What you see | Cause | What to do |
| --- | --- | --- |
| `access_denied` / "An error has occurred" instead of a code | Duke's login rejected the browser | Use the helper, or switch the browser to a mobile User-Agent and start a fresh flow |
| "Not Found" page and no code | That page is the expected landing page; the code is in its address bar | Copy the whole address and paste it into **Callback URL** |
| "That URL belongs to a different sign-in attempt" | The pasted URL came from an older flow | Open the sign-in link from the current form again and paste the new address |
| Helper popup shows no code | The helper is disabled or lacks site access | Check `chrome://extensions` → Details → site access includes `login.duke-energy.com`; reload the helper |
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
