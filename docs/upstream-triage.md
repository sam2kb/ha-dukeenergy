# ha-dukeenergy — upstream triage and fork plan

**Date:** 2026-10-19
**Upstream:** [hunterjm/ha-dukeenergy](https://github.com/hunterjm/ha-dukeenergy) — MIT, 43★, 9 forks, default branch `main` @ `3108a71`
**Our fork:** [sam2kb/ha-dukeenergy](https://github.com/sam2kb/ha-dukeenergy) — public, created 2026-10-19
**Method:** GitHub API sweep of every issue, PR and fork; full diff review of every fork that
has unique commits; crash0verride11's test suite cloned and executed in a container. No live
Duke Energy account was used, so authentication findings are code-and-discussion evidence, not
a live reproduction.

---

## TL;DR

- Upstream is alive but maintenance-light. The last functional code change was March 2026;
  since then only dependency bumps and one version bump (v0.3.1, 2026-09-19). The maintainer
  has said publicly that his day job limits review throughput and that forks are welcome
  ([#18, 2026-03-06](https://github.com/hunterjm/ha-dukeenergy/issues/18#issuecomment-4013986974)).
- The real problem is **authentication fragility**, not missing features. Three different
  blocks exist at three different points in the OAuth chain. Two are fixed; one (desktop
  browser login, October 2026) is fixed only in an unmerged extension PR.
- Feature work already exists in forks: gas, cost statistics, sensors, bill-cycle data,
  better polling, tests. [crash0verride11's v2.1.4](https://github.com/crash0verride11/ha-dukeenergy)
  is a superset of everything else and its 52-test suite passes. It is the best base.
- Upstream also has two correctness bugs worth fixing regardless of base: statistics are
  wiped on every reload/restart, and any CDN block is treated as a lost credential (the
  "continually re-authenticates" loop).
- **Recommendation:** release line based on crash0verride11 v2.1.4, plus a vendored Chrome
  extension with the iOS User-Agent rewrite, plus our own CI, docs and release discipline.
  Keep the integration domain `duke_energy` so existing statistics history survives.

---

## 1. Where upstream stands

| Signal | Value |
| --- | --- |
| Stars / forks | 43 / 9 |
| Last release | v0.3.1, 2026-09-19 (`aiodukeenergy==1.1.1`) |
| Last functional commit | `73c9e61 refactor: android to iOS OAuth (#22)`, 2026-03-05 |
| Open issues | 9 |
| Open PRs | 7 (4 about auth/gas/cost, 3 stale dependabot) |
| Tests in repo | none |
| CI | ruff, hassfest, HACS validation, release-version check |
| Pinned HA in `requirements.txt` | 2025.12.5 |

The repository is a working integration, not abandoned, but it is not keeping pace with
Duke's bot-protection changes. The maintainer merged a user-agent fix in September only
after a fork author diagnosed it (`aiodukeenergy` PR #22).

---

## 2. The authentication problem

Duke moved to Auth0 in November 2025. The flow is:

1. A browser opens `https://login.duke-energy.com/authorize` with Duke's iOS client ID,
   PKCE and the iOS callback `https://login.duke-energy.com/ios/com.duke-energy.app/callback`.
2. The callback is a dead page on Duke's domain, so the browser cannot hand the code back to
   HA. A browser extension watches the navigation and forwards `code` + `state` to HA.
3. HA exchanges the code at `https://login.duke-energy.com/oauth/token` (PKCE) and stores the
   three tokens.
4. `aiodukeenergy` exchanges the Auth0 `id_token` at
   `https://api-v2.cma.duke-energy.app/login/auth-token` for a Duke API token, then calls the
   API with that token.

There are **three distinct block points**, and they are routinely confused in the issue
tracker:

| # | Where | Symptom | Status |
| --- | --- | --- | --- |
| A | Duke API `/login/auth-token` and API calls (Akamai) | `403 Access Denied`, HTML body, `errors.edgesuite.net` reference | **Fixed** by updating the mobile User-Agent in `aiodukeenergy` 1.1.1 (2026-09-19, PR #22) |
| B | `login.duke-energy.com/authorize` (Auth0 hosted login) | redirects with `error=access_denied` *before* any token exchange | **Not fixed upstream.** Desktop browsers are rejected; an iPhone UA completes the same URL. Workaround: DevTools device emulation; real fix: extension rewrites the UA ([jdobbsclt PR #23](https://github.com/hunterjm/aiodukeenergy/pull/23)) |
| C | Any of the above, transiently | a block is raised as `DukeEnergyAuthError`, HA starts a reauth flow | **Not fixed upstream.** crash0verride11's lib distinguishes `DukeEnergyBlockedError` and retries instead of prompting |

Evidence for B is community-reported and consistent: jdobbsclt reproduced desktop vs iPhone
User-Agent behaviour and traced it to the authorize step
([#62 comment, 2026-10-19](https://github.com/hunterjm/ha-dukeenergy/issues/62#issuecomment-6257026862)),
and ar34uy independently reported `access_denied` at `/authorize/resume`
([#57 comment, 2026-10-16](https://github.com/hunterjm/ha-dukeenergy/pull/57#issuecomment-6219149706)).
A does not explain B: `#62` fails before the token exchange, and jdobbsclt reproduced B on
v0.3.1 with the current `aiodukeenergy`.

### 2.1 Why upstream loops on "re-authenticate"

`coordinator.py` does:

```python
except DukeEnergyAuthError as err:
    raise ConfigEntryAuthFailed from err
```

`aiodukeenergy` 1.1.1 raises `DukeEnergyAuthError` for *every* non-200 from the
`/login/auth-token` endpoint, including Akamai HTML blocks. So a CDN hiccup becomes a
credential verdict, HA raises a repair, and the user re-authenticates against a login page
that may reject their browser (B). That is the loop in
[#62](https://github.com/hunterjm/ha-dukeenergy/issues/62).

A fix needs both halves: a distinct "blocked" exception in the client, and mapping it to
`UpdateFailed` (retry next poll) rather than `ConfigEntryAuthFailed`. crash0verride11 has
both; jameslb has an equivalent `fix blocked Duke authentication client` commit.

### 2.2 The statistics-wipe bug

Upstream registers `self.config_entry.async_on_unload(self._clear_statistics)` in the
coordinator constructor. Every unload — reload, HA restart, integration disable — deletes the
external statistics this integration wrote. On next setup it re-fetches up to three years and
recomputes sums from zero. That is why the Energy dashboard can lose history, and it is
independent of the auth sagas. crash0verride11 moved the clear to `async_remove_entry` only.

---

## 3. Issues

### Authentication

| # | State | Ask / report | Verdict |
| --- | --- | --- | --- |
| [#18](https://github.com/hunterjm/ha-dukeenergy/issues/18) | closed | 53-comment Android→iOS auth saga; Sept recurrence from stale UA | Historic. Fix shipped in v0.3.1. Keep as reference for UA regressions |
| [#59](https://github.com/hunterjm/ha-dukeenergy/issues/59) | closed | OAuth succeeds, token exchange 403 | Reporter fixed by v0.3.1 — symptom A |
| [#58](https://github.com/hunterjm/ha-dukeenergy/issues/58) | closed | Token exchange failed | Duplicate of #59 |
| [#62](https://github.com/hunterjm/ha-dukeenergy/issues/62) | **open** | Reauth prompt never clears; 403 at token exchange; later `access_denied` at authorize | **Priority.** Symptom A (fixed for one user), C (loop) and B (desktop UA) all in one thread. Needs the blocked-error + UA-extension work, then a clear reply |
| [#38](https://github.com/hunterjm/ha-dukeenergy/issues/38) | **open** | Login lands on "Not Found" page | Same family as B. The "Not Found" is the expected iOS callback page, but the flow only completes if the extension captures it; desktop-UA rejection now short-circuits earlier |
| [#37](https://github.com/hunterjm/ha-dukeenergy/issues/37) | **open** | Add OAuth token instructions to the integration page | Docs. Our README/strings should explain the extension and the 404 page |
| [#55](https://github.com/hunterjm/ha-dukeenergy/issues/55) | **open** | "No code was captured" | Duke outage, per the only reply. Close as not planned |

### Gas

| # | State | Ask / report | Verdict |
| --- | --- | --- | --- |
| [#21](https://github.com/hunterjm/ha-dukeenergy/issues/21) | **open** | Piedmont Natural Gas support | Different account system; no evidence the CMA API exposes it. Park pending an account that can prove the endpoint |

Duke-branded gas meters are a different matter and are supported by crash0verride11 and by
PR #27 — see below.

### Cost and entities

| # | State | Ask / report | Verdict |
| --- | --- | --- | --- |
| [#53](https://github.com/hunterjm/ha-dukeenergy/issues/53) | **open** | Publish an opower-style cost statistic so the Energy dashboard can track $ | **Build.** Confirmed by three investigators: the API has no per-interval cost. Derive cost from a user price source (entity or fixed rate). PR #54 and crash0verride11 both implement this |
| [#7](https://github.com/hunterjm/ha-dukeenergy/issues/7) | **open** | Create an energy sensor for Utility Meter / cost tracking | The maintainer's objection (data is ~24 h old) is correct for a real-time sensor, but bill-cycle usage sensors and cost statistics solve the underlying need without lying about "now". crash0verride11 ships those |
| [#52](https://github.com/hunterjm/ha-dukeenergy/issues/52) | **open** | Allow the energy source to be renamed | HA's Energy dashboard now supports a display name per source (noted in the thread). Answer and close; statistic IDs must not change or history breaks |

### Timing

| # | State | Ask / report | Verdict |
| --- | --- | --- | --- |
| [#15](https://github.com/hunterjm/ha-dukeenergy/issues/15) | **open** | When does the integration sync? | Answer in docs: upstream polls every 12 h; crash0verride11 polls around 09:00/14:00/19:00 ET with a ±2 h per-install offset |

---

## 4. Pull requests

Nine non-dependabot PRs exist: four open, three merged, two closed unmerged. Separately,
three stale dependabot PRs are open.

| PR | Author | Size | What | Verdict |
| --- | --- | --- | --- | --- |
| [#57](https://github.com/hunterjm/ha-dukeenergy/pull/57) | jdahmen | +175/−32, 5 files, CONFLICTING | Manual callback URL paste; drops the extension | **Do not merge as the primary auth path.** It bypasses the extension but still opens the login page in a desktop browser, which is exactly what now fails (B). Conflicts are trivial (manifest version + strings.json). Worth harvesting as an *optional* fallback for users who can emulate a phone |
| [#54](https://github.com/hunterjm/ha-dukeenergy/pull/54) | jojobird6 | +838/−79, 11 files, MERGEABLE | Cost statistics, options flow, fixed price / price entity / monthly charge, backfill, tests | **Strong design reference.** Mergeable and well argued. If we do not take crash0verride11's cost implementation, this is the one to take |
| [#27](https://github.com/hunterjm/ha-dukeenergy/pull/27) | crash0verride11 | +36/−10, 1 file, MERGEABLE | Gas support: DAILY/WEEK, volume units, noon timestamps | **Superseded** by the author's own fork, which contains the same logic plus tests. Useful as the minimal-diff explanation |
| [#25](https://github.com/hunterjm/ha-dukeenergy/pull/25) | ndemarco | +26/−11, 3 files, CONFLICTING | Gas support stacked on #22 | **Close as superseded.** Same logic as #27, older base |
| [#24](https://github.com/hunterjm/ha-dukeenergy/pull/24) | ndemarco | closed | iOS auth + gas | Superseded by merged #22 |
| [#56](https://github.com/hunterjm/ha-dukeenergy/pull/56) | jameslb | +1664/−124, 15 files, closed by author | Gas + costs + manual callback + token validation | **Mine for ideas, do not merge.** Pins `aiodukeenergy` as a git URL in `manifest.json`, which HACS/HA cannot install reliably |
| [#51](https://github.com/hunterjm/ha-dukeenergy/pull/51) | dependabot | — | home-assistant/actions bump | Handle by updating our own workflows |
| [#50](https://github.com/hunterjm/ha-dukeenergy/pull/50) | dependabot | — | ruff 0.15.16 | Bump ourselves |
| [#49](https://github.com/hunterjm/ha-dukeenergy/pull/49) | dependabot | — | pip >=26.1.2 | Bump ourselves |

Merged already: #5 (id_token expiry), #8 (version alignment), #22 (iOS OAuth refactor),
#26/#28/#10/#20 (dependabot), #60 (requirements/version bump).

---

## 5. Forks

| Fork | Unique commits | What is in it | Verdict |
| --- | --- | --- | --- |
| [crash0verride11](https://github.com/crash0verride11/ha-dukeenergy) (`ha-dukeenergy-aio`, 6★) | 73 | Gas + temperature statistics; per-meter cost statistics with a full options flow (sensor price, static price, backfill); per-account and per-meter devices/sensors (status, last/next poll, bill-cycle usage, billing/payment); three-window randomized polling; correct statistics lifecycle; blocked-vs-auth error split; 52 tests | **Best base.** Test suite passes (`52 passed` against HA 2026.2.3). Requires its own PyPI client `aiodukeenergy-co>=1.3.0` |
| [jameslb](https://github.com/jameslb/ha-dukeenergy) | 13 | Gas; effective-dated rate periods; credential reconfigure; diagnostics entities; manual callback; tests | **Second-best design source.** Not distributable as-is: git-URL dependency, issues disabled, no release |
| [jdobbsclt](https://github.com/jdobbsclt/ha-dukeenergy) | 1 (+ `aiodukeenergy` PR #23) | Time-of-use cost patch (hard-coded Duke residential rates); **extension rule that sends an iOS Safari UA to `login.duke-energy.com`** | **Critical handpick:** the extension rule. The TOU patch is a personal rate hack; a price entity covers it properly |
| [jdahmen](https://github.com/jdahmen/ha-dukeenergy) | 1 | Manual callback paste (PR #57) | Optional fallback; see PR table |
| [jojobird6](https://github.com/jojobird6/ha-dukeenergy) | 3 | Cost statistics (PR #54) | Design reference / fallback if not using crash0verride11 |
| [ndemarco](https://github.com/ndemarco/ha-dukeenergy) | 5 | Gas meter support (PRs #24, #25) | Superseded |
| slammingprogramming, flkns, 23brewert | 0 | Clones / dependabot only | Ignore |

### The client library

`aiodukeenergy` (PyPI, 1.1.1) is also thin on maintenance. Open work there:

- [#23](https://github.com/hunterjm/aiodukeenergy/pull/23) — extension UA rewrite (**critical**, open)
- [#20](https://github.com/hunterjm/aiodukeenergy/pull/20) — daily energy usage fixes (open)
- [#18](https://github.com/hunterjm/aiodukeenergy/pull/18) — Safari extension (open)
- [#19](https://github.com/hunterjm/aiodukeenergy/issues/19) — `-30 days` range bug (open)

crash0verride11 maintains `aiodukeenergy-co` on PyPI (1.3.0, 2026-09-17) with the blocked
error type, gas/monthly endpoints and the current User-Agent. That package is what the
recommended base depends on.

---

## 6. Gap analysis — what nobody has fixed

1. **Desktop login rejection (B).** Only jdobbsclt's extension rule addresses it. No
   integration-side change can fix it, because the login happens in the user's browser.
2. **A reliable distribution story for the extension.** Upstream hosts the zip on the *library*
   repo; crash0verride11 hosts it on the integration release. Neither is documented in HA's
   UI, and both still ship the pre-fix extension.
3. **Blocked vs. rejected auth on the integration side for upstream users.** Fixed only in
   forks.
4. **Statistics lifecycle.** Fixed only in forks.
5. **Tests and CI for integration logic.** Only forks have them; upstream has no test job.
6. **Dependabot rot.** Three open PRs, two closed per week; nobody merges them.
7. **Docs.** README still says "Chrome on desktop, extension required", with no troubleshooting
   for the 404 page, `access_denied`, or the reauth loop.

---

## 7. Recommended fork strategy

### Option A — adopt crash0verride11 v2.1.4 as the base (recommended)

Create `release/v2` from crash0verride11's `ha-dukeenergy-aio` @ `5a517d3`, re-brand the
manifest/README/CI to our fork, vendor the extension with the UA rule, and release 2.2.0.

- **Pros:** everything in §6.3–6.5 is already done and tested; gas, cost, sensors and polling
  are real user value; 52 tests give us a safety net; MIT allows it with attribution.
- **Cons:** inherits a dependency on one person's PyPI package and their release cadence; we
  become a downstream of a downstream; rebranding and attribution need care.
- **Mitigation:** pin `aiodukeenergy-co` exactly, keep a thin adapter in `api.py`, and keep
  the door open to switching the client later. Coordinate with crash0verride11 rather than
  compete.

### Option B — clean base on upstream v0.3.1 + cherry-picks

Merge #54 (cost), #27 (gas), #57 (manual callback), and rewrite the auth-error mapping and
statistics lifecycle ourselves.

- **Pros:** smallest diff, easiest to review, stays on the official `aiodukeenergy` package,
  easiest to upstream.
- **Cons:** re-implements work that already exists; inherits the two upstream correctness bugs
  until we fix them; #57 is not a working auth fix on its own; no sensors; no test harness.
  Realistically several weekends to reach parity.

### Option C — hybrid

Upstream base plus crash0verride11's coordinator/auth/statistics fixes, but keep our own
feature work.

- **Pros:** smaller than A, more capable than B.
- **Cons:** crash0verride11's code is entangled with `aiodukeenergy-co` (monthly usage, billing
  endpoints); cherry-picking produces a half-migrated client. Highest conflict cost per unit
  of value.

**Choose A.** The thing users need is a working login and trustworthy history, and A is the
only path that delivers both without re-deriving a year of reverse engineering.

---

## 8. What we build ourselves (regardless of base)

1. **Extension with the UA rule.**
   Vendor `chrome-extension/` in our repo, apply jdobbsclt's `rules.json` (declarativeNetRequest
   UA rewrite scoped to `login.duke-energy.com`, stripping `Sec-CH-UA*`), bump the extension
   version, and attach `chrome-extension.zip` to every release. Document the DevTools
   workaround for users who will not install an extension.
2. **Auth-failure taxonomy.**
   `DukeEnergyBlockedError → UpdateFailed` (retry), `DukeEnergyAuthError → ConfigEntryAuthFailed`
   (reauth), network errors → `ConfigEntryNotReady`. Add tests for each mapping.
3. **Statistics lifecycle.**
   Never clear on unload; clear only in `async_remove_entry`. Test that a reload preserves
   sums.
4. **Docs that match reality.**
   Install → extension → 404 page is expected → reauth → troubleshooting table mapping
   `403 Access Denied`, `access_denied`, "Not Found", "No code captured" to causes.
5. **CI.**
   Keep ruff + hassfest + HACS validation; add `pytest` against the pinned HA version and the
   next one; fail the release if `manifest.json` version ≠ tag.
6. **Release hygiene.**
   Tag `v2.2.0`, attach the extension zip, keep `hacs.json` current. Delete the inherited
   stale branches on the fork.
7. **Attribution.**
   Keep the MIT license and copyright; add a short `CREDITS.md` naming hunterjm,
   crash0verride11, jdobbsclt, jojobird6, jdahmen, jameslb and ndemarco for the pieces we use.

---

## 9. Phased plan

**Phase 0 — fork hygiene (done / this branch)**
Fork created, upstream triage written, remotes mapped.

**Phase 1 — import the base (½ day)**
```sh
git remote add crash https://github.com/crash0verride11/ha-dukeenergy.git
git fetch crash ha-dukeenergy-aio
git switch -c release/v2 crash/ha-dukeenergy-aio
```
Re-brand `manifest.json` (`codeowners`, `documentation`, `issue_tracker`), `hacs.json`,
README, workflows; keep domain `duke_energy` and pin `aiodukeenergy-co==1.3.0`.
Run the test suite and ruff before changing anything.

**Phase 2 — make login work today (1 day)**
Vendor the extension with the UA rule; publish a release asset; document install. This is the
only change that fixes new installs right now.

**Phase 3 — correctness and tests (1–2 days)**
Auth-failure taxonomy tests, statistics lifecycle test, options-flow tests. Add the pytest
workflow.

**Phase 4 — absorb the best of the rest (1–2 days)**
Port #54's cost UX details if crash0verride11's is weaker (monthly charge, price-entity
history fallback), and jameslb's effective-dated rate periods if we want scheduled rate
changes. Add the manual-callback fallback from #57 behind a clearly labelled option.

**Phase 5 — release and support (ongoing)**
Tag v2.2.0, write release notes that explain the auth changes, answer the open issues with
what shipped, and set a triage cadence.

---

## 10. Risks and open questions

**Risks**

- **UA arms race.** Both fixes are User-Agent spoofing. Akamai or Auth0 can tighten again
  (TLS fingerprinting would defeat the extension rule). Keep a fast-release path and watch the
  extension.
- **Supply chain.** `aiodukeenergy-co` is a personal package. Pin exact versions, review
  diffs, and consider mirroring it under our account if it becomes load-bearing.
- **Upstream drift.** If hunterjm revives the project, we should be able to merge him rather
  than fork forever. Keep changes modular.
- **HA version drift.** Upstream pins HA 2025.12.5; crash0verride11's tests resolved 2026.2.3.
  Pick an explicit minimum and test the current release.
- **No live verification here.** None of the auth fixes can be proven without a Duke account.
  Ship behind a clear "report your result" ask and a diagnostics dump.

**Decisions needed**

1. Base: crash0verride11 v2.1.4 (A) vs clean upstream (B) vs hybrid (C)? → recommendation: **A**.
2. Do we coordinate with crash0verride11 (send the extension fix and blocked-error tests
   upstream to him) or run fully independent releases?
3. Client library: stay on `aiodukeenergy-co`, or publish our own maintained fork of
   `aiodukeenergy`?
4. Do we keep `sam2kb/ha-dukeenergy` as the public home, or rename the repo once the release
   line exists?

---

## 11. Appendix — data

- Upstream branch head: `3108a71` (2026-09-19).
- Candidate heads:
  - crash0verride11 `ha-dukeenergy-aio` `5a517d3` (2026-09-18), manifest 2.1.4,
    `aiodukeenergy-co>=1.3.0`
  - jdobbsclt `tou-cost` `10d1943` (2026-10-18)
  - jameslb `agent/auth-resilience-diagnostics` `3183446` (2026-09-25)
  - jdahmen `jdahmen/auth` `61cad01` (2026-09-16)
  - jojobird6 `feat/cost-statistics` `422c893` (2026-07-09)
  - ndemarco `feat/gas-meter-support` `339f451` (2026-03-04)
- Test run: `uv sync --all-groups && .venv/bin/python -m pytest -q` on crash0verride11's tree
  in `ghcr.io/astral-sh/uv:python3.13-bookworm` → **52 passed**.
- Fork counts: 9 total; 6 with unique commits; 3 clones.

### Mapping of every open issue and PR to an action

| Item | Action |
| --- | --- |
| #62 | Close the loop with the blocked-error fix + extension UA; ask for diagnostics if it persists |
| #55 | Close as not planned (Duke outage) |
| #53 | Ship cost statistics |
| #52 | Answer (Energy dashboard display name) and close |
| #38 | Answer with the corrected flow + UA workaround; keep open until B is fixed |
| #37 | Covered by new README / strings |
| #21 | Park; needs an account that can prove the API surface |
| #15 | Document polling schedule |
| #7 | Ship bill-cycle usage sensors + cost statistics; explain why not a real-time sensor |
| PR #57 | Harvest as optional fallback, do not merge |
| PR #54 | Design reference for costs |
| PR #27 | Superseded by crash0verride11's fork |
| PR #25 | Close as superseded |
| PR #51/#50/#49 | Bump dependencies ourselves |
