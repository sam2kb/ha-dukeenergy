# Credits

This integration is a fork of
[hunterjm/ha-dukeenergy](https://github.com/hunterjm/ha-dukeenergy), which in
turn grew out of the Home Assistant custom-integration blueprint by
[Joakim Sørensen (@ludeeus)](https://github.com/ludeeus).

The 2.2.0 release line is based on
[crash0verride11/ha-dukeenergy v2.1.4](https://github.com/crash0verride11/ha-dukeenergy).

## Code and design

| Contributor | Contribution |
| --- | --- |
| [Jason Hunter (@hunterjm)](https://github.com/hunterjm) | Original integration, the Auth0/OAuth rework, and the `aiodukeenergy` client |
| [@crash0verride11](https://github.com/crash0verride11) | iOS OAuth refactor, the mobile User-Agent fix, gas and temperature statistics, per-meter cost statistics and options flow, account/meter devices, three-window polling, the statistics lifecycle fix, blocked-vs-auth error handling, the test suite this fork builds on, and the [billing-cycle rollover fix](https://github.com/crash0verride11/ha-dukeenergy/commit/f316ba0b7979236d8b0ba3f97fde57e2d0d4b6d9) |
| [@jdobbsclt](https://github.com/jdobbsclt) | Diagnosed the October 2026 desktop-browser login rejection and the User-Agent workaround (`aiodukeenergy` PR #23) |
| [@jojobird6](https://github.com/jojobird6) | Cost-statistic design, local cost recovery from stored consumption, and the investigation showing Duke's API exposes no per-interval cost ([PR #54](https://github.com/hunterjm/ha-dukeenergy/pull/54), issue #53) |
| [@jdahmen](https://github.com/jdahmen) | Manual callback-URL config flow (`ha-dukeenergy` PR #57) |
| [@jameslb](https://github.com/jameslb) | Auth-resilience, diagnostics and effective-dated rate work (`ha-dukeenergy` PR #56 and fork branches) |
| [@b-v-co](https://github.com/b-v-co) | Identified the October 2026 account-list route and response changes and supplied the [upstream fix](https://github.com/hunterjm/aiodukeenergy/pull/25) adapted here |
| [@ndemarco](https://github.com/ndemarco) | Early gas meter support (`ha-dukeenergy` PRs #24, #25) |

## Reverse engineering and community research

- [jnjustice/Duke-Energy-Data-Collector](https://github.com/jnjustice/Duke-Energy-Data-Collector)
- [mjmeli/pyduke-energy](https://github.com/mjmeli/pyduke-energy)
- [w1ll1am23/pydukeenergy](https://github.com/w1ll1am23/pydukeenergy)
- Everyone who reported token-exchange failures with logs and reproductions in
  the upstream issue tracker.

## License

The bundled Duke Energy icons and logos come from
[Home Assistant Brands](https://github.com/home-assistant/brands/tree/master/custom_integrations/duke_energy).

MIT. See [LICENSE](LICENSE); the original copyright notices are preserved.
