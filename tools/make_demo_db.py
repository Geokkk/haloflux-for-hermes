# DEMO ONLY — builds a demo state.db with purely fictional data.
# All totals, session titles and counts below are made-up sample
# values for screenshots and testing; they are NOT real usage data.
import sqlite3, os, sys
p = sys.argv[1] if len(sys.argv) > 1 else "demo-state.db"
if os.path.exists(p): os.remove(p)
con = sqlite3.connect(p)
con.execute("""CREATE TABLE sessions (
  id TEXT PRIMARY KEY, title TEXT, model TEXT, billing_provider TEXT,
  source TEXT, started_at TEXT, ended_at TEXT,
  message_count INTEGER, tool_call_count INTEGER,
  input_tokens INTEGER, output_tokens INTEGER,
  cache_read_tokens INTEGER, cache_write_tokens INTEGER,
  reasoning_tokens INTEGER, api_call_count INTEGER,
  estimated_cost_usd REAL, actual_cost_usd REAL, last_activity_at TEXT)""")
con.execute("""CREATE TABLE messages (
  id INTEGER PRIMARY KEY, session_id TEXT, role TEXT,
  tool_name TEXT, timestamp INTEGER, token_count INTEGER, tool_calls TEXT)""")
inp_total, out_total, cr_total = 12345678, 234567, 34567890
msgs_total, tools_total = 1234, 567
rows = []
for i in range(22):
    rows.append((f"s{i:02d}", f"Demo session {i+1:02d} - sample history", "nvidia/nemotron-3-ultra-550b-a55b",
                 "xai", "app", "2026-11-09 00:00:00 UTC", "2026-11-09 01:00:00 UTC",
                 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, "2026-11-09 01:00:00 UTC"))
cur = ("cur1", "Demo session - planning a trip", "nvidia/nemotron-3-ultra-550b-a55b",
       "xai", "app", "2026-11-10 02:49:47 UTC", None,
       42, 12, 123456, 6543, 234567, 0, 0, 8, 0.0, 0.0, "2026-11-10 08:59:10 UTC")
rows.append(cur)
rows[0] = ("s00", "Demo session 01 - sample history", "nvidia/nemotron-3-ultra-550b-a55b",
           "xai", "app", "2026-11-09 00:00:00 UTC", "2026-11-09 01:00:00 UTC",
           msgs_total-42, tools_total-12, inp_total-123456, out_total-6543, cr_total-234567,
           0, 0, 15, 0.0, 0.0, "2026-11-09 01:00:00 UTC")
con.executemany("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
con.execute("INSERT INTO messages VALUES (1,'cur1','assistant','browser_navigate',1762820000,100,'[]')")
con.execute("INSERT INTO messages VALUES (2,'cur1','user',NULL,1762820100,50,NULL)")
con.execute("INSERT INTO messages VALUES (3,'s00','assistant','terminal',1762700000,10,'[]')")
con.commit(); con.close()
print("demo db built:", p)
