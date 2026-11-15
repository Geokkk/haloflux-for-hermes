"""
HALOFLUX · AI LINK — Hermes dashboard plugin backend
======================================================
Mounted by the Hermes web dashboard at /api/plugins/haloflux/ because
dashboard/manifest.json declares "api": "plugin_api.py". Routes sit
behind the dashboard's normal auth gate (unauthenticated -> 401).

GET /api/plugins/haloflux/stats   one HALOFLUX snapshot (shape identical
                                  to the upstream ai-link-server.js)
GET /api/plugins/haloflux/health  {"ok": bool} — ok is a real read-only
                                  probe of state.db, not a constant.
GET /api/plugins/haloflux/bgm     the bundled BGM track (audio/mpeg).
                                  Served via the API because the
                                  dashboard's plugin static server only
                                  serves a whitelist of extensions — .mp3
                                  404s there (verified live 2026-11-15:
                                  same-directory .mp3 -> 404 while a .js
                                  one subdirectory deeper -> 200).

Data source: ~/.hermes/state.db, opened read-only (sqlite URI mode=ro),
one fresh connection per sample. Only aggregates and metadata columns
are read; message bodies / system prompts are never selected. This is
the same reader as the standalone hermes-ai-link.py adapter, minus its
HTTP server — the dashboard process hosts the routes instead.

Design decisions (deliberate — read before changing):
1. Headline totals are CUMULATIVE across all sessions (SUM over the
   sessions table), not the current session alone. The video HUD this
   replicates shows cumulative-scale numbers (604.31M tokens / 18,526
   tools / 21,701 messages / 52 sessions), so cumulative is the faithful
   reading. Live fields (model, sessionTitle, tokens/s) come from the
   current session.
2. "Current session" = ended_at IS NULL, ordered by the latest
   messages.timestamp for that session — NOT by sessions.last_activity_at
   (proven stale on 2026-11-11: it read 2026-11-10 08:59 UTC while the
   conversation was still running) and NOT by started_at alone.
   Fallback (no messages rows): latest started_at.
3. cache_write_tokens IS included in tokensTotal when present.
4. tokensPerSec / outputTokensPerSec: 10 s trailing window on the
   cumulative totals (same algorithm as the original updateTokenRate).
   First ~10 s after dashboard start the rate is 0 — expected.
5. steps = null (no Hermes column; the frontend tolerates null and
   lists it in `nulls`). turns = SUM(api_call_count) approximation.
   activeAgents = count of sessions with ended_at IS NULL.
6. System side is the dashboard host's own — correct here because
   the data subject IS this host. Host sampling is platform-
   dispatched (see "Platform support" below): Linux reads /proc
   (stat, meminfo, net/dev, per-process stat/status). gpu = null
   (no GPU on the reference host); never fake values.
7. Handlers are plain `def` (not async) so FastAPI runs them in a worker
   thread — the sqlite reads never block the dashboard event loop.
8. Column guards apply to EVERY query, not just the totals: sessions /
   messages column sets are read via PRAGMA and every referenced column
   is substituted with a `NULL AS <col>` placeholder when missing, so
   older state.db schemas degrade instead of raising OperationalError.
   The current-session messages join aggregates MAX(timestamp) in a
   GROUP BY subquery first, so it never scans messages more than once.
9. Failure degradation: stats() catches sqlite3.Error (missing DB,
   table-less DB, locked DB) and returns an offline snapshot with the
   same shape (link=False, zeroed counts, no current session) — never
   a bare 500. Snapshots are cached for 3 s; while the DB is locked
   the last good snapshot is served instead of an error.
10. Shared mutable state (rate window, CPU baseline, snapshot cache)
    is guarded by one threading.Lock, because handlers run in a
    thread pool (see 7).
11. The DB path is resolved per connection (env may change without a
    dashboard restart) and converted with Path.as_uri(); snapshots
    expose only the DB file name, never its absolute path.

Platform support: the Hermes-side fields (ai.*) are pure sqlite and
work anywhere. Host sampling (cpu / cpuCores / ram / net / top /
topAll / procCount) goes through a per-platform sampler table keyed
by sys.platform (_HOST_SAMPLERS). Linux is implemented (pure /proc,
zero subprocess, standard library only); darwin / win32 are reserved
— no sampler is registered for them yet, so on those platforms the
host fields degrade to null and the frontend renders its empty
states. To add a platform, write sampler functions returning the
same shapes and register them in _HOST_SAMPLERS; _assemble and the
routes do not change.

DB path: $HERMES_DB, else $HERMES_HOME/state.db, else ~/.hermes/state.db.
"""
import json
import os
import sqlite3
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

VERSION = "1.3.0"

RATE_WINDOW_MS = 10000
CACHE_TTL_MS = 3000
STARTED_AT = time.time()
_rate_samples = deque()  # (t_ms, total, output)
_lock = threading.Lock()
_cache = {"snap": None, "at_ms": 0, "db": None}

router = APIRouter()


def _round(v, d):
    return round(v, d) if v is not None else None


def _db_path():
    # Resolved per connection (design decision 11), never frozen at
    # import time.
    if os.environ.get("HERMES_DB"):
        return os.environ["HERMES_DB"]
    if os.environ.get("HERMES_HOME"):
        return os.path.join(os.environ["HERMES_HOME"], "state.db")
    return os.path.join(os.path.expanduser("~"), ".hermes", "state.db")


def _connect_ro():
    # Fresh connection per sample: cheap, never holds a WAL lock, and
    # always sees the latest committed rows. Path.as_uri() keeps paths
    # containing '?' / '#' / spaces from opening the wrong file.
    uri = Path(_db_path()).expanduser().absolute().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=2.0)


def _ts_ms(v):
    """messages.timestamp -> epoch ms, tolerating TEXT/float storage."""
    if v is None:
        return None
    try:
        return int(float(v) * 1000)
    except (TypeError, ValueError):
        return None


def _epoch_s(v):
    """sessions.started_at -> epoch seconds.

    started_at is stored inconsistently across Hermes versions:
    epoch numbers in some, ISO text ('2026-11-09 00:00:00 UTC') in
    others. Tolerate both; return None when unparseable."""
    if v is None:
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        pass
    try:
        t = str(v).replace(" UTC", "+00:00")
        if t.endswith("Z"):
            t = t[:-1] + "+00:00"
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None


def read_hermes():
    """Return aggregates + current-session metadata from state.db."""
    con = _connect_ro()
    try:
        cur = con.cursor()
        cols = {r[1] for r in cur.execute("PRAGMA table_info(sessions)")}
        mcols = {r[1] for r in cur.execute("PRAGMA table_info(messages)")}

        def s(col):
            return "COALESCE(SUM(%s),0)" % col if col in cols else "0"

        totals = cur.execute(
            "SELECT COUNT(*), %s, %s, %s, %s, %s, %s, %s FROM sessions"
            % (s("message_count"), s("tool_call_count"), s("input_tokens"),
               s("output_tokens"), s("cache_read_tokens"),
               s("cache_write_tokens"), s("api_call_count"))
        ).fetchone()
        (n_sessions, messages, tool_calls, inp, outp,
         cache_read, cache_write, api_calls) = totals
        tokens_total = inp + outp + cache_read + cache_write

        # Current session: live first, by freshest message activity.
        # last_activity_at is NOT trusted (proven stale 2026-11-11).
        # Every column below is guarded against the PRAGMA column set
        # (design decision 8): missing -> NULL placeholder, never a
        # hard-coded name that can raise OperationalError.
        cur_cols = ("id", "title", "model", "billing_provider",
                    "message_count", "tool_call_count", "input_tokens",
                    "output_tokens", "cache_read_tokens", "started_at")

        def sel(col, prefix=""):
            return ("%s%s" % (prefix, col)) if col in cols \
                else ("NULL AS %s" % col)

        def sel_list(prefix=""):
            return ", ".join(sel(c, prefix) for c in cur_cols)

        def live_where(prefix=""):
            if "ended_at" in cols:
                return "%sended_at IS NULL" % prefix
            return "1=1"  # no ended_at column: liveness unknowable

        def started_key(prefix=""):
            return "%sstarted_at" % prefix if "started_at" in cols \
                else "%srowid" % prefix

        cur_row = None
        tables = {r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if ("messages" in tables and "id" in cols
                and {"session_id", "timestamp"} <= mcols):
            cur_row = cur.execute(
                """SELECT %s
                   FROM sessions s
                   LEFT JOIN (SELECT session_id, MAX(timestamp) AS max_ts
                              FROM messages GROUP BY session_id) lm
                     ON lm.session_id = s.id
                   WHERE %s
                   ORDER BY lm.max_ts DESC, %s DESC LIMIT 1"""
                % (sel_list("s."), live_where("s."), started_key("s."))
            ).fetchone()
        if cur_row is None:
            cur_row = cur.execute(
                """SELECT %s FROM sessions
                   WHERE %s ORDER BY %s DESC LIMIT 1"""
                % (sel_list(), live_where(), started_key())
            ).fetchone()
        if cur_row is None:  # no live session: fall back to the newest one
            cur_row = cur.execute(
                """SELECT %s FROM sessions ORDER BY %s DESC LIMIT 1"""
                % (sel_list(), started_key())
            ).fetchone()

        if "ended_at" in cols:
            live = cur.execute(
                "SELECT COUNT(*) FROM sessions WHERE ended_at IS NULL"
            ).fetchone()[0]
        else:
            live = 1 if cur_row is not None else 0

        last_event = last_event_type = last_event_at = None
        if (cur_row is not None and cur_row[0] is not None
                and {"session_id", "timestamp", "tool_name"} <= mcols):
            ev = cur.execute(
                """SELECT tool_name, timestamp FROM messages
                   WHERE session_id = ? AND tool_name IS NOT NULL
                   ORDER BY timestamp DESC LIMIT 1""",
                (cur_row[0],)).fetchone()
            if ev:
                last_event = "tool/call · %s" % ev[0]
                last_event_type = "tool/call"
                last_event_at = _ts_ms(ev[1])
        if (last_event is None and cur_row is not None
                and cur_row[0] is not None
                and {"session_id", "timestamp", "role"} <= mcols):
            ev = cur.execute(
                """SELECT role, timestamp FROM messages
                   WHERE session_id = ? ORDER BY timestamp DESC LIMIT 1""",
                (cur_row[0],)).fetchone()
            if ev:
                last_event = ev[0]
                last_event_type = ev[0]
                last_event_at = _ts_ms(ev[1])

        # Recent tool calls: metadata only. The query selects exactly
        # two columns — tool_name, timestamp — never any body or
        # tool-call payload column (red line, see header).
        recent_tools = []
        if {"tool_name", "timestamp"} <= mcols:
            try:
                now_ms_rt = int(time.time() * 1000)
                for tname, tts in cur.execute(
                        """SELECT tool_name, timestamp FROM messages
                           WHERE tool_name IS NOT NULL
                           ORDER BY timestamp DESC LIMIT 8"""):
                    at_ms = _ts_ms(tts)
                    recent_tools.append({
                        "name": tname,
                        "at": at_ms if at_ms is not None else 0,
                        "ageSec": max(0, int((now_ms_rt - at_ms) / 1000))
                                  if at_ms is not None else 0,
                    })
            except sqlite3.Error:
                recent_tools = []

        # Per-model session aggregates, presented as the frontend's
        # "agents" list: Hermes is a single agent, so grouping its
        # sessions by model is the honest equivalent of the upstream
        # multi-agent roster. lastActive prefers the freshest message
        # timestamp in the group (last_activity_at is not trusted,
        # decision 2); started_at is only a fallback and may be ISO
        # text, so it is coerced via _epoch_s. A missing model column
        # makes grouping meaningless -> degrade to [].
        agents = []
        if "model" in cols:
            try:
                def gsum(col):
                    return ("COALESCE(SUM(%s),0)" % col) \
                        if col in cols else "0"

                tok_expr = "+".join(gsum(c) for c in
                                    ("input_tokens", "output_tokens",
                                     "cache_read_tokens",
                                     "cache_write_tokens"))
                live_expr = ("SUM(CASE WHEN s.ended_at IS NULL"
                             " THEN 1 ELSE 0 END)") \
                    if "ended_at" in cols else "0"
                started_expr = "s.started_at" \
                    if "started_at" in cols else "NULL"
                if ("messages" in tables and "id" in cols
                        and {"session_id", "timestamp"} <= mcols):
                    join_sql = (" LEFT JOIN (SELECT session_id,"
                                " MAX(timestamp) AS max_ts FROM messages"
                                " GROUP BY session_id) lm"
                                " ON lm.session_id = s.id")
                    last_msg_expr = "MAX(lm.max_ts)"
                else:
                    join_sql = ""
                    last_msg_expr = "NULL"
                arows = cur.execute(
                    """SELECT COALESCE(NULLIF(s.model, ''), 'unknown')
                              AS agent,
                              COUNT(*), %s, %s, %s, %s, %s, MAX(%s)
                       FROM sessions s%s
                       GROUP BY agent ORDER BY 4 DESC LIMIT 8"""
                    % (live_expr, tok_expr, gsum("message_count"),
                       gsum("tool_call_count"), last_msg_expr,
                       started_expr, join_sql)).fetchall()
                now_s = time.time()
                for r in arows:
                    la = r[6] if r[6] is not None else _epoch_s(r[7])
                    la = int(la) if la is not None else 0
                    agents.append({
                        "agent": r[0], "sessions": int(r[1]),
                        "activeSessions": int(r[2] or 0),
                        "tokensTotal": int(r[3] or 0),
                        "messages": int(r[4] or 0),
                        "toolCalls": int(r[5] or 0),
                        "lastActive": la,
                        "active": bool(la and (now_s - la) <= 180),
                    })
            except sqlite3.Error:
                agents = []

        return {
            "sessions": n_sessions, "messages": messages,
            "tool_calls": tool_calls, "input": inp, "output": outp,
            "cache_read": cache_read, "cache_write": cache_write,
            "tokens_total": tokens_total, "api_calls": api_calls,
            "live_sessions": live, "current": cur_row,
            "last_event": last_event, "last_event_type": last_event_type,
            "last_event_at": last_event_at,
            "recent_tools": recent_tools, "agents": agents,
        }
    finally:
        con.close()


_cpu_prev = None


def _sample_cpu_linux():
    global _cpu_prev
    try:
        with open("/proc/stat") as f:
            parts = f.readline().split()[1:]
        vals = [int(x) for x in parts]
    except Exception:
        return None
    total, idle = sum(vals), vals[3] + (vals[4] if len(vals) > 4 else 0)
    now = (idle, total)
    with _lock:
        if _cpu_prev is None:
            _cpu_prev = now
            return None
        d_total = total - _cpu_prev[1]
        d_idle = idle - _cpu_prev[0]
        _cpu_prev = now
    if d_total <= 0:
        return None
    return _round(100.0 * (1 - d_idle / d_total), 1)


def _sample_ram_linux():
    try:
        mem = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, _, v = line.partition(":")
                mem[k.strip()] = int(v.split()[0])  # kB
        total, avail = mem["MemTotal"], mem["MemAvailable"]
        used_pct = 100.0 * (1 - avail / total)
        return {"usedPct": _round(used_pct, 1),
                "usedGB": _round((total - avail) / 1048576.0, 2),
                "totalGB": _round(total / 1048576.0, 2)}
    except Exception:
        return None


# ---------------------------------------------------------------------
# Host sampling: platform dispatch (v1.2).
#
# Every sampler below is looked up in _HOST_SAMPLERS by sys.platform.
# Only Linux is implemented; on darwin / win32 the lookup misses and
# the public wrappers return None, so the snapshot fields stay null
# and the frontend degrades — samplers must never raise and never
# touch another platform's files. Adding a platform = adding sampler
# functions with the same return shapes + one table entry.
#
# Differential samplers (cores / procs / net) keep their previous
# reading in _host_prev under the shared _lock, mirroring the
# _cpu_prev pattern: the first call only establishes the baseline.
# ---------------------------------------------------------------------

_PLATFORM = sys.platform
try:
    _CLK_TCK = os.sysconf("SC_CLK_TCK")
except (ValueError, OSError, AttributeError):
    _CLK_TCK = 100

_host_prev = {}  # kind -> (wall_time, payload)


def _prev_diff(kind, payload):
    """Swap the stored baseline for kind; return (dt_sec, old)."""
    now = time.time()
    with _lock:
        old = _host_prev.get(kind)
        _host_prev[kind] = (now, payload)
    if old is None:
        return None
    return now - old[0], old[1]


def _read_proc_stat():
    """Parse /proc/stat -> (total_jiffies, idle_jiffies,
    [(core_total, core_idle), ...]); None when unreadable."""
    total = idle = None
    cores = []
    with open("/proc/stat") as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "cpu":
                vals = [int(x) for x in parts[1:]]
                total = sum(vals)
                idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
            elif parts[0].startswith("cpu") and parts[0][3:].isdigit():
                vals = [int(x) for x in parts[1:]]
                cores.append((sum(vals),
                              vals[3] + (vals[4] if len(vals) > 4 else 0)))
    if total is None:
        return None
    return total, idle, cores


def _sample_cores_linux():
    try:
        st = _read_proc_stat()
    except Exception:
        return None
    if st is None:
        return None
    cores = st[2]
    d = _prev_diff("cores", cores)
    if d is None or len(d[1]) != len(cores):
        return None
    dt, old = d
    out = []
    for (t, i), (ot, oi) in zip(cores, old):
        d_total = t - ot
        if d_total <= 0:
            out.append(0)
        else:
            out.append(int(round(100.0 * (1 - (i - oi) / d_total))))
    return out


def _read_proc_list():
    """One /proc sweep -> {pid: (name, jiffies, starttime, mem_mb)}.

    name is the exe basename when readable, else the stat comm.
    The process argument vector is never read (it can carry flags,
    paths and secrets); comm/exe carry the program name only."""
    try:
        pids = [e for e in os.listdir("/proc") if e.isdigit()]
    except OSError:
        return None
    procs = {}
    for e in pids:
        try:
            with open("/proc/%s/stat" % e, "rb") as f:
                raw = f.read().decode("utf-8", "replace")
            lp, rp = raw.find("("), raw.rfind(")")
            comm = raw[lp + 1:rp]
            rest = raw[rp + 2:].split()
            jiff = int(rest[11]) + int(rest[12])  # utime + stime
            start = int(rest[19])                 # starttime
            mem_mb = 0.0
            try:
                with open("/proc/%s/status" % e) as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            mem_mb = int(line.split()[1]) / 1024.0
                            break
            except OSError:
                pass
            name = comm
            try:
                exe = os.readlink("/proc/%s/exe" % e)
                if exe:
                    name = os.path.basename(
                        exe.split(" (deleted)")[0]) or comm
            except OSError:
                pass
            procs[int(e)] = (name, jiff, start, mem_mb)
        except (OSError, ValueError, IndexError):
            continue  # exited mid-read / unparsable: skip this pid
    return procs


def _sample_procs_linux():
    """-> (top12, top40, total_count) or None.

    CPU% is a two-sweep differential against the previous sweep
    (same jiffies source as /proc/stat, CLK_TCK ticks per second),
    expressed on a one-core basis. The first sweep has no baseline,
    so every process reports cpu 0.0 that once; real values arrive
    with the next snapshot (~3 s later, the snapshot cache TTL)."""
    procs = _read_proc_list()
    if procs is None:
        return None
    d = _prev_diff("procs", procs)
    items = []
    for pid, (name, jiff, start, mem_mb) in procs.items():
        cpu = 0.0
        if d is not None:
            dt, old = d
            o = old.get(pid)
            # starttime match guards against pid reuse between sweeps.
            if o is not None and o[2] == start and dt > 0:
                cpu = 100.0 * ((jiff - o[1]) / _CLK_TCK) / dt
        items.append({"name": name,
                      "cpu": _round(max(0.0, cpu), 1),
                      "memMB": _round(mem_mb, 1),
                      "icon": None})
    items.sort(key=lambda p: (-p["cpu"], -p["memMB"], p["name"]))
    return items[:12], items[:40], len(items)


def _sample_net_linux():
    try:
        rx = tx = 0
        with open("/proc/net/dev") as f:
            for line in f:
                if ":" not in line:
                    continue
                iface, _, rest = line.partition(":")
                if iface.strip() == "lo":
                    continue
                fields = rest.split()
                rx += int(fields[0])   # receive bytes
                tx += int(fields[8])   # transmit bytes
    except Exception:
        return None
    total_mb = _round((rx + tx) / 1048576.0, 1)
    d = _prev_diff("net", (rx, tx))
    if d is None:
        return {"rxPerSec": 0, "txPerSec": 0, "totalMB": total_mb}
    dt, (orx, otx) = d
    if dt <= 0:
        return {"rxPerSec": 0, "txPerSec": 0, "totalMB": total_mb}
    return {"rxPerSec": int(max(0, (rx - orx) / dt)),
            "txPerSec": int(max(0, (tx - otx) / dt)),
            "totalMB": total_mb}


_HOST_SAMPLERS = {
    "linux": {"cpu": _sample_cpu_linux, "ram": _sample_ram_linux,
              "cores": _sample_cores_linux, "procs": _sample_procs_linux,
              "net": _sample_net_linux},
    # "darwin": reserved — register psutil-free samplers here later.
    # "win32":  reserved — ditto (performance counters / psapi).
}


def _host_sampler(kind):
    return _HOST_SAMPLERS.get(_PLATFORM, {}).get(kind)


def sample_cpu():
    fn = _host_sampler("cpu")
    return fn() if fn else None


def sample_ram():
    fn = _host_sampler("ram")
    return fn() if fn else None


def sample_cores():
    fn = _host_sampler("cores")
    return fn() if fn else None


def sample_procs():
    """-> (top, topAll, procCount) or None on unsupported/failed."""
    fn = _host_sampler("procs")
    return fn() if fn else None


def sample_net():
    fn = _host_sampler("net")
    return fn() if fn else None


def update_rate(now_ms, total, output):
    with _lock:
        _rate_samples.append((now_ms, total, output))
        while _rate_samples and now_ms - _rate_samples[0][0] > RATE_WINDOW_MS:
            _rate_samples.popleft()
        if len(_rate_samples) < 2:
            return 0, 0, 0
        first = _rate_samples[0]
        span = (now_ms - first[0]) / 1000.0
        if span < 0.5:
            return 0, 0, _round(span, 1)
        return (_round(max(0, (total - first[1]) / span), 2),
                _round(max(0, (output - first[2]) / span), 2),
                _round(span, 1))


def _assemble(now_ms, d, link, tps, otps, window):
    cpu = sample_cpu()
    ram = sample_ram()
    cores = sample_cores()
    net = sample_net()
    procs = sample_procs()
    cur = d["current"]
    hit_denom = d["cache_read"] + d["input"]
    ai = {
        "tokensTotal": d["tokens_total"],
        "tokensPerSec": tps,
        "toolCalls": d["tool_calls"],
        "messages": d["messages"],
        "sessions": d["sessions"],
        "activeAgents": d["live_sessions"],
        "model": cur[2] if cur else None,
        "lastEvent": d["last_event"],
        "sessionTitle": cur[1] if cur else None,
        "outputTokensPerSec": otps,
        "cacheHitRate": _round(100.0 * d["cache_read"] / hit_denom, 1) if hit_denom else None,
        "provider": cur[3] if cur else None,
        "sessionId": cur[0] if cur else None,
        "sessionMessages": cur[4] if cur else None,
        "sessionTools": cur[5] if cur else None,
        "recentTools": d.get("recent_tools") or [],
        "agents": d.get("agents") or [],
        "sessionFile": None,
        "sessionUpdatedAt": d["last_event_at"],
        "lastEventType": d["last_event_type"],
        "lastEventAgeSec": max(0, int((now_ms - d["last_event_at"]) / 1000)) if d["last_event_at"] else None,
        "inputTokens": d["input"],
        "outputTokens": d["output"],
        "cacheReadTokens": d["cache_read"],
        "contextTokens": None,
        "turns": d["api_calls"],
        "steps": None,
        "jobsRunning": None,
        "tokensWindowSec": window,
    }
    snap = {
        "ts": now_ms,
        "tsIso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "link": link,
        "cpu": cpu,
        "cpuCores": cores,
        "cpuName": None,
        "cpuCount": os.cpu_count(),
        "ram": ram["usedPct"] if ram else None,
        "net": net,
        "ramDetail": ram,
        "gpu": None,
        "top": procs[0] if procs else None,
        "topAll": procs[1] if procs else None,
        "procCount": procs[2] if procs else None,
        "uptimeSec": int(time.time() - STARTED_AT),
        "ai": ai,
        "nulls": [],
        "server": {"version": VERSION, "pid": os.getpid(), "port": None,
                   "startedAt": int(STARTED_AT * 1000), "node": None,
                   "host": os.uname().nodename, "platform": sys.platform,
                   "arch": os.uname().machine, "cores": os.cpu_count(),
                   "sessionsDir": os.path.basename(_db_path())},
    }
    for k in ("cpu", "ram", "gpu", "cpuCores", "net", "top"):
        if snap[k] is None:
            snap["nulls"].append(k)
    for k, v in ai.items():
        if v is None:
            snap["nulls"].append("ai." + k)
    return snap


def build_snapshot():
    now_ms = int(time.time() * 1000)
    d = read_hermes()
    tps, otps, window = update_rate(now_ms, d["tokens_total"], d["output"])
    return _assemble(now_ms, d, True, tps, otps, window)


def _offline_snapshot(now_ms):
    # Same shape as a live snapshot (design decision 9): link=False,
    # counts zeroed, no current session. The frontend falls back to
    # its offline rendering on this instead of dying on a 500.
    d = {"sessions": 0, "messages": 0, "tool_calls": 0, "input": 0,
         "output": 0, "cache_read": 0, "cache_write": 0,
         "tokens_total": 0, "api_calls": 0, "live_sessions": 0,
         "current": None, "last_event": None, "last_event_type": None,
         "last_event_at": None, "recent_tools": [], "agents": []}
    return _assemble(now_ms, d, False, 0, 0, 0)


@router.get("/stats")
def stats():
    now_ms = int(time.time() * 1000)
    path = _db_path()
    with _lock:
        if (_cache["snap"] is not None and _cache["db"] == path
                and now_ms - _cache["at_ms"] < CACHE_TTL_MS):
            return _cache["snap"]
    try:
        snap = build_snapshot()
    except sqlite3.Error:
        # Missing / table-less / locked DB: serve the last good
        # snapshot if we have one, else a structured offline snapshot.
        with _lock:
            if _cache["snap"] is not None and _cache["db"] == path:
                return _cache["snap"]
        return _offline_snapshot(int(time.time() * 1000))
    with _lock:
        _cache["snap"] = snap
        _cache["at_ms"] = now_ms
        _cache["db"] = path
    return snap


@router.get("/health")
def health():
    ok = False
    try:
        con = _connect_ro()
        try:
            con.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
            ok = True
        finally:
            con.close()
    except sqlite3.Error:
        ok = False
    return {"ok": ok, "version": VERSION}


@router.get("/bgm")
def bgm():
    """Serve the bundled BGM track (see header note on the static
    server's extension whitelist). Behind the same auth gate as
    /stats; the <audio> element requests it same-origin."""
    p = (Path(__file__).parent / "dist" / "haloflux" / "audio"
         / "sw421k.mp3")
    if not p.is_file():
        raise HTTPException(status_code=404, detail="bgm not bundled")
    return FileResponse(p, media_type="audio/mpeg",
                        filename="sw421k.mp3")
