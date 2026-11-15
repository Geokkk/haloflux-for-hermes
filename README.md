# HALOFLUX for Hermes

> The HALOFLUX halo telemetry visualisation, wired to your own Hermes Agent data — as a dashboard plugin page.

[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.3.0-green)](dashboard/manifest.json)
[![Tested on](https://img.shields.io/badge/tested%20on-Hermes%20Agent%20v0.23.0-orange)](#compatibility)

**English** · [简体中文](README.zh-CN.md)

![HALOFLUX for Hermes — live demo data](docs/images/hero.png)

*Screenshot with fictional demo data — yours will show your own Hermes numbers.*

HALOFLUX for Hermes is a plugin page for the Hermes Agent dashboard. It takes the
HALOFLUX ring visualisation — central halo, a band of live data cards, eight data
panels along the bottom, a HUD in the top-right — and drives all of it from Hermes's
own data: session/token/tool telemetry read from the local `state.db`, plus host
system sampling. Nothing is mocked: every number on the page comes from the machine
the dashboard is running on.

This is a third-level derivative work (see [Credits & license](#credits--license)).
**Noncommercial use only.**

## Features

- **Live ring band cards** showing real host processes — name, CPU, memory, network.
- **Eight data panels**, all fed by real data (see [Panels](#panels)).
- **HUD + top KPIs**: current session, model, token total, throughput, cache hit
  rate, tool calls, messages, sessions.
- **BGM with a spectrum window**: a bundled track, a 7-band spectrum visualiser in
  the lower-left that dances with the music, and two ways to use your own music
  (see [BGM & spectrum](#bgm--spectrum)).
- **Zero-dependency backend**: Python standard library only, no build step. The
  frontend is plain HTML/JS served by the dashboard itself.
- **Private by design**: read-only database access, metadata columns only, no
  message bodies, everything behind the dashboard login (see
  [Data & privacy](#data--privacy)).

## Compatibility

- **Tested on Hermes Agent v0.23.0.** No other version is claimed compatible.
- You need a Hermes dashboard you can log into, and file access to the machine
  running it (to drop the plugin in and restart the dashboard).

## Quick install

### One-click script (recommended)

From a checkout of this repository:

```bash
# Linux / macOS
./scripts/install.sh

# Windows (PowerShell)
.\scripts\install.ps1
```

The script copies `dashboard/` into `~/.hermes/plugins/haloflux/dashboard/`,
backing up any previous version first. It does not touch any configuration and
does not restart anything.

### Manual

Copy the `dashboard/` directory from this repository so that it lands at:

```
~/.hermes/plugins/haloflux/dashboard/
```

### Then

1. Restart the Hermes dashboard.
2. Log into the dashboard in your browser.
3. Click **HALOFLUX** in the dashboard sidebar (under Plugins), or open
   `/haloflux` directly (e.g. `http://<your-dashboard-host>/haloflux`) — some
   frontends (e.g. the mobile app webview) don't render plugin entries.

Environment variables:

- `HERMES_HOME` — use a different Hermes home directory (default `~/.hermes`).
- `HERMES_DB` — point the plugin at a specific `state.db`. Restart the dashboard
  after changing either variable.

## How it works

```
Hermes state.db (read-only) ─┐
                             ├─► plugin_api.py ─► /api/plugins/haloflux/stats (JSON snapshot)
Host sampling (Linux /proc) ─┘        ▲                    │
                                      │                    ▼
                              dashboard process      ai-link frontend (this page)
```

The plugin backend (`dashboard/plugin_api.py`) builds a small JSON snapshot —
Hermes telemetry aggregated from `state.db`, plus CPU / per-core CPU / memory /
network / process sampling — caches it for a few seconds, and serves it from a
same-origin endpoint inside the dashboard process. The frontend polls that
endpoint once per second and drives the halo, the ring cards, the panels and the
HUD. There is no separate server and no extra port.

## Data & privacy

- **Read-only**: the backend opens `state.db` read-only and never writes to it.
- **Metadata only**: it queries session/message *metadata* columns — counts,
  token totals, tool names, timestamps. It **never reads message bodies**.
- **Behind the login**: every plugin endpoint, including the stats JSON and the
  BGM stream, sits behind the dashboard's own login. An unauthenticated request
  to the stats endpoint returns **401 — that is the expected, healthy behaviour**,
  not an error.
- **No telemetry, no external requests**: the plugin phones nowhere. The page
  makes no external requests at all — fonts are your system font stack, and all
  assets (including the BGM track) are served locally by the dashboard.
- **Process sampling is name/CPU/memory only.** Command lines are never read.

## BGM & spectrum

The plugin ships with one bundled track (the upstream original, covered by the
upstream license) and a 7-band spectrum window in the lower-left of the stage
that reacts to whatever is playing. To use your own music, two ways:

1. **In the page (per browser):** click **本地音乐 / Local music** in the
   top-right of the page and pick an audio file from your device. It is stored
   in your browser (IndexedDB), survives reloads, and a **默认 / Default**
   button switches back to the bundled track at any time. If a local file turns
   out to be unplayable, the player falls back to the bundled track instead of
   dying.
2. **On the server (for every visitor):** replace
   `dashboard/dist/haloflux/audio/sw421k.mp3` in the installed plugin with your
   own MP3, keeping the file name. No restart is needed — the track is streamed
   through the plugin's `/api/plugins/haloflux/bgm` route (behind the same
   login), which reads the file per request.

> Only use music you have the rights to use. The in-browser option keeps your
> file on your own device, which is usually the better choice for
> copyrighted tracks.

## Panels

| # | Panel | What it shows |
|---|-------|---------------|
| 1 | AI event stream | Recent tool calls by real tool name, newest first |
| 2 | Token throughput | Live tok/s curve from a rolling window, plus cache hit rate |
| 3 | Session status | Model, current session, its message/tool counts, uptime, last event |
| 4 | CPU / GPU load | Host CPU (total + per-core) and GPU where available |
| 5 | Data link | Plugin link state, poll interval, session file count, plugin version |
| 6 | Tools / messages | Tool-call and message totals with live increments |
| 7 | Agent scheduling | Sessions grouped by model — sessions, active count, tokens, tools per model |
| 8 | System load index | CPU / GPU / memory / network activity heat rows |

The ring band cards show the host's top processes (name, CPU, memory, network
rate). **GPU fields show "unavailable" on machines without a GPU — that is
expected**, not a bug.

## Platform support

The AI data (tokens, sessions, tools, panels) is identical on every platform.
Host sampling — process list, per-core CPU, network rates — is currently
implemented for **Linux** only; on Windows and macOS those spots honestly show
blank / `—` instead of fake numbers. See [DESKTOP.md](DESKTOP.md) for the
desktop breakdown and the roadmap.

## Design notes

A few hard-won details, recorded so you don't have to rediscover them:

- **`state.db` schema varies between versions.** Columns may be missing, so the
  backend guards every column it uses and degrades to `null` / empty lists
  instead of erroring. A missing column should never turn into a 500.
- **"Current session" is not just `started_at` / `ended_at`.** Old sessions can
  keep a stale "not ended" flag, so the current session is picked with a
  composite check (open flag, latest message activity, start time) rather than
  a single column.
- **Rates are differences of cumulative counters.** tok/s is computed from a
  short rolling window over the cumulative token totals — the same counters the
  KPI strip shows — so the curve and the totals can never disagree.
- **WAL mode + read-only opens.** The backend relies on the live database files
  (including the `-wal` sidecar) being readable; pointing `HERMES_DB` at a bare
  copied `.db` file while Hermes is running can serve stale data.

## Test record

Verified against a fictional demo database generated by
[`tools/make_demo_db.py`](tools/make_demo_db.py) (12,345,678 input /
234,567 output / 34,567,890 cache-read tokens, 1,234 messages, 567 tool calls,
23 sessions — all invented):

| Scenario | Result |
|----------|--------|
| Demo DB baseline | Every aggregate reconciles field-by-field with the generated data |
| DB with missing columns | Degrades gracefully, no 500s |
| Empty DB / no DB | Offline snapshot served, page shows its offline state |
| Write-locked DB | Falls back to the last good cached snapshot |
| 8 concurrent request threads | No errors, consistent snapshots |
| Real deployment | v1.3.0 deployed and accepted on a live Hermes Agent v0.23.0 (ring cards, all panels, spectrum, local-music BGM) |

## Differences from upstream ai-link

- **Carrier**: upstream is a Wallpaper Engine wallpaper plus a standalone
  Node.js service; this version is a Hermes dashboard plugin — no separate
  process, no extra port.
- **Auth**: upstream used its own shared token and a JSONP fallback. This
  version removes JSONP and the standalone-service access pattern entirely and
  relies on the dashboard login instead.
- **Data source**: upstream reads DeepSeek Harness / Ekko Studio databases;
  this version reads Hermes Agent's own `state.db` and adds Linux host
  sampling.

## Credits & license

Attribution chain (full text in [NOTICE](NOTICE)):

1. **HALOFLUX** by **Ryder191** — https://github.com/Ryder191/haloflux
2. **HALOFLUX · AI LINK** by **yeshuiwushen** — https://github.com/yeshuiwushen/haloflux-ai-link
3. **HALOFLUX for Hermes** — this repository, a dashboard-plugin port of the above.

Licensed under the **PolyForm Noncommercial License 1.0.0** — the upstream
license text is reproduced in full in [LICENSE](LICENSE). **Noncommercial use
only**; no commercial licenses are offered. The original work, including its
source code and audiovisual design, remains the copyright of Ryder191.
