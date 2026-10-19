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
| [@crash0verride11](https://github.com/crash0verride11) | iOS OAuth refactor, the mobile User-Agent fix, gas and temperature statistics, per-meter cost statistics and options flow, account/meter devices, three-window polling, the statistics lifecycle fix, blocked-vs-auth error handling, and the test suite this fork builds on |
| [@jdobbsclt](https://github.com/jdobbsclt) | Diagnosed the October 2026 desktop-browser login rejection and the User-Agent workaround (`aiodukeenergy` PR #23) |
| [@jojobird6](https://github.com/jojobird6) | Cost-statistic design and the investigation showing Duke's API exposes no per-interval cost (`ha-dukeenergy` PR #54, issue #53) |
| [@jdahmen](https://github.com/jdahmen) | Manual callback-URL config flow (`ha-dukeenergy` PR #57) |
| [@jameslb](https://github.com/jameslb) | Auth-resilience, diagnostics and effective-dated rate work (`ha-dukeenergy` PR #56 and fork branches) |
| [@ndemarco](https://github.com/ndemarco) | Early gas meter support (`ha-dukeenergy` PRs #24, #25) |

## Reverse engineering and community research

- [jnjustice/Duke-Energy-Data-Collector](https://github.com/jnjustice/Duke-Energy-Data-Collector)
- [mjmeli/pyduke-energy](https://github.com/mjmeli/pyduke-energy)
- [w1ll1am23/pydukeenergy](https://github.com/w1ll1am23/pydukeenergy)
- Everyone who reported token-exchange failures with logs and reproductions in
  the upstream issue tracker.

## License

MIT. See [LICENSE](LICENSE); the original copyright notices are preserved.
