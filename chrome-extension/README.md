# Duke Energy OAuth Helper

A Chrome/Edge extension for the [Duke Energy Home Assistant integration](https://github.com/sam2kb/ha-dukeenergy).

Duke Energy's login only accepts its mobile app's OAuth redirect, so the browser
cannot hand the authorization code back to Home Assistant. This extension
watches for that redirect, forwards the code to Home Assistant, and — since
October 2026 — makes `login.duke-energy.com` see an iPhone Safari User-Agent so
Duke stops rejecting desktop browsers with `access_denied` after the password
step.

## Install

### From the release zip

1. Download `chrome-extension.zip` from the
   [latest release](https://github.com/sam2kb/ha-dukeenergy/releases/latest).
2. Extract it to a folder you will keep (Chrome reloads an unpacked extension
   from that path, so don't leave it in Downloads and delete it later).
3. Open `chrome://extensions/` (or `edge://extensions/`).
4. Enable **Developer mode**.
5. Click **Load unpacked** and select the extracted folder.

### From source

Load this `chrome-extension/` directory directly with **Load unpacked**.

## Use

1. Start adding (or re-authenticating) the integration in Home Assistant.
2. Open the login link Home Assistant shows and sign in.
3. Duke redirects to a "Not Found" page. That page is expected.
4. The extension captures the code and forwards it to Home Assistant
   automatically.

If the automatic forward does not happen, open the extension popup and copy the
captured code/URL manually.

## What the User-Agent rule does

`rules.json` is a Manifest V3 `declarativeNetRequest` rule. It applies only to
`login.duke-energy.com` and only changes the `User-Agent` and the `Sec-CH-UA*`
client hints. Every other site, and every API call Home Assistant makes itself,
is untouched.

Duke's login rejects desktop browsers (verified October 2026: the same authorize
URL succeeds with an iPhone User-Agent and fails without one). The rule is
scoped to the login host so the rest of your browsing is unaffected.

## Security notes

- The authorization code is short-lived and single-use.
- The extension asks for `webNavigation`, `tabs` and `declarativeNetRequest`,
  with host access only to `https://login.duke-energy.com/*`.
- It does not read or store your Duke credentials; the login form is Duke's own.
