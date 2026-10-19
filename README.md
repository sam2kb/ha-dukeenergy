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
It adds a browser sign-in flow with a pasted callback URL, config-entry
diagnostics, tests in CI and release-version checks. See
[CREDITS.md](CREDITS.md).

> [!WARNING]
> This integration uses Duke Energy's private mobile API. It is unofficial and
> can break whenever Duke changes its app, its login or its bot protection. It
> is maintained on a best-effort basis, not as a supported product.

## Requirements

- Home Assistant 2026.2 or later
- A desktop browser for the one-time sign-in (Firefox, Safari, Chrome or Edge)
- A Duke Energy account with electric and/or gas service
- HACS (recommended) or manual installation

Configuration is through the Home Assistant UI; no YAML or application
credentials are needed. Home Assistant's recorder must be enabled.

## Install

### 1. Install the integration

Add this repository to HACS as a custom repository:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sam2kb&repository=ha-dukeenergy&category=integration)

Or, in HACS: **Custom repositories** → add
`https://github.com/sam2kb/ha-dukeenergy` → category **Integration** → install →
restart Home Assistant.

Manual install: copy `custom_components/duke_energy/` into your HA
`config/custom_components/` directory and restart.

### 2. Sign in

Duke's login uses its mobile app's redirect URI and checks the browser's
User-Agent. Sign in with a mobile User-Agent, then paste the resulting callback
URL into Home Assistant.

**Step 1 - open setup:** go to **Settings → Devices & services → Add
integration → Duke Energy**. Open the sign-in link and keep the Home Assistant
setup form open.

**Step 2 - set a mobile User-Agent in the Duke sign-in tab:**

- **Firefox:** open `about:config`, add a **String** named
  `general.useragent.override`, and paste the iPhone value below. Firefox has no
  per-site override, so reset the pref when you are done.
- **Safari:** enable the Develop menu, then
  **Develop → User Agent → Safari — iOS 18 — iPhone**.
- **Chrome/Edge:** press `F12`, then `Ctrl+Shift+M`, and pick an iPhone.

Keep developer tools open in Chrome/Edge while signing in. After changing the
User-Agent, open the original sign-in link from the setup form in that prepared
tab. Reloading an error page alone will not restart authorization.

**Step 3 - copy the callback:** after signing in, Duke lands on a "Not Found"
page whose address ends in `?code=…&state=…`. Copy the **whole** address from the
address bar and paste it into **Callback URL**.

Treat this URL as a sign-in credential: paste it only into the setup form,
and keep it out of issue reports and screenshots. Reset any temporary browser
User-Agent override when you are done.

**Step 4 - wait for the import:** after you submit, setup downloads up to three
years of usage. This can take a minute or two; don't remove the integration
while it initializes. The account's `Status` sensor then shows `Fetching`,
`Recording`, and finally `Finished`.

```
Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1
```

### 3. Add usage to the Energy dashboard

Once the account's **Status** is **Finished**:

1. Open **Settings → Dashboards → Energy**.
2. Under **Electricity grid**, add grid consumption and select the Duke Energy
   electric consumption statistic for your meter.
3. For gas service, add the corresponding statistic under **Gas consumption**.
4. Save, then choose a date with imported usage to view the history.

Consumption and calculated costs are external statistics. They appear in the
Energy dashboard's selectors and **Developer tools → Statistics**, rather than
as consumption entities under **Developer tools → States**. The bill-cycle
sensors are summaries and should not be selected as Energy dashboard sources.

## If the sign-in fails

| What you see | Cause | What to do |
| --- | --- | --- |
| `access_denied` / "An error has occurred" instead of a code | Duke's login still saw a desktop browser | Apply the mobile User-Agent, then start a fresh sign-in |
| "Not Found" page with `code` and `state` in the address | This is the expected landing page | Copy the whole address into **Callback URL** |
| No `code` in the address | Sign-in did not complete | Reopen the current setup form's sign-in link with the mobile User-Agent applied |
| "That URL belongs to a different sign-in attempt" | The pasted URL came from an older flow | Open the sign-in link from the current form again and paste the new address |
| Setup seems stuck after submitting | It is importing up to three years of usage in 30-day windows | Wait a minute or two; check **Settings → System → Logs** only if it exceeds several minutes |
| `403 Access Denied` on token exchange | Duke's API edge blocked the request | Update the integration through HACS; if it persists, open an issue with diagnostics |
| Reauthentication prompt never clears | A transient block was treated as a bad credential | Update to 2.2.0+; if it persists, download diagnostics (**Settings → Devices & services → Duke Energy → ⋮ → Download diagnostics**) and attach it to an issue |

## Cost tracking

After setup, open the integration's **Configure** dialog and pick a meter:

- **Entity price:** a sensor's long-term statistics supply historical prices,
  so a template sensor can represent time-of-use or seasonal rates. If there
  are no price statistics in the fetched window, a numeric current state is
  used as a flat rate. This also allows `number` and `input_number` entities.
- **Static price:** one fixed rate.
- **Do not track:** stops adding costs for that meter and keeps existing cost
  history.

Enter prices per **kWh** for electricity or per **CCF** for gas, in Home
Assistant's configured currency. For a dollar rate, 15 cents/kWh is `0.15`.
These are usage-based estimates; fixed charges, taxes and other bill adjustments
are not added automatically.

Choose **Save and apply**, then submit the historical-cost form. Without a
backfill, the new settings apply at the next poll. Existing cost rows stay in
place, and only intervals newer than the last cost row are added. When you
first enable costs, this can include recently fetched usage.

**Backfill historical cost** reloads the integration and recomputes stored usage
history for every meter with cost tracking enabled. A static rate applies to
the whole history. With a price entity, gaps carry the preceding price forward;
usage before the first recorded price uses that earliest price. If no price
history exists, the current numeric value prices the whole history. Backfill
replaces historical cost values, so enable it only when you intend to reprice
them. It does not change consumption history.

Cost is written as an external statistic
(`duke_energy:electric_<serial>_energy_cost`) so the Energy dashboard can track
costs with **Use an entity tracking the total costs**.

Select the cost statistic that matches the consumption meter. Cost statistics
use Home Assistant's configured currency (USD if unset); no currency conversion
is performed.

## When data updates

Duke publishes usage with a delay. The integration polls around **09:00, 14:00
and 19:00 America/New_York**, each shifted earlier or later by up to two hours.
The offset comes from the config entry ID and date. It stops for the day once
every supported meter has usage for yesterday. Setup and reload also trigger
an immediate poll. **Next scheduled update** shows the actual next attempt;
**Last updated** records an attempt, including a failed one.

## Statistics and entities

| Thing | Example |
| --- | --- |
| Electric consumption | `duke_energy:electric_<serial>_energy_consumption` (kWh, hourly) |
| Gas consumption | `duke_energy:gas_<serial>_energy_consumption` (CCF, daily at noon) |
| Cost | `duke_energy:<type>_<serial>_energy_cost` (configured HA currency) |
| Temperature | `duke_energy:account_<id>_temperature` (°F, daily) |

Devices: one per account (`Status`, `Last updated`, `Next scheduled update`,
bill-cycle and last-year costs, bill balance/due date/status) and one per meter
(`Last changed`, bill-cycle and last-year usage).

### Updating and removing

Update through HACS and restart Home Assistant. For a manual update, replace
the `custom_components/duke_energy/` folder and restart. Keep the existing
integration entry; use its reauthentication prompt if sign-in is needed again.

Statistics persist across reloads, updates and restarts. Deleting the **last
Duke Energy login** from **Devices & services** deletes all Duke Energy external
statistics, including calculated costs and temperature history. If another Duke
Energy login remains configured, statistics are kept because meters can be
shared between logins. Back up Home Assistant before removing the last login
if you want to retain that history.

## Reporting a problem

Include your Home Assistant and integration versions, whether the problem
affects electricity or gas, the steps to reproduce it, and what you expected.
Download diagnostics from **Settings → Devices & services → Duke Energy → ⋮ →
Download diagnostics** when available. Diagnostics hide tokens and replace meter
identifiers with local labels while keeping update times and cost settings.

For a reproducible failure, enable debug logging from the integration's menu,
reproduce the problem, then disable it to download the log. Review attachments
before posting: logs can include account details, service addresses and API
responses. Remove personal information, tokens and callback URLs. A setup
failure may occur before diagnostics can be downloaded; the error and a
redacted log excerpt are enough to start a report.

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
- **Manual imports.** This integration does not import Duke's Green Button
  downloads. Using those files in the Energy dashboard requires separate
  import tooling.

## Credits

See [CREDITS.md](CREDITS.md). MIT licensed, see [LICENSE](LICENSE).
