"""SQLite incident store: dedupes open incidents and tracks status (open/acknowledged/resolved)."""
import os
import sqlite3
from datetime import datetime

DB = os.getenv("INCIDENT_DB", "incidents.db")


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS incidents(
            id INTEGER PRIMARY KEY AUTOINCREMENT, service TEXT, template TEXT, severity TEXT,
            count INTEGER, first_seen TEXT, last_seen TEXT, samples TEXT, root_cause TEXT, fix TEXT,
            rca_source TEXT, status TEXT DEFAULT 'open', created TEXT)""")


def upsert(inc):
    """Returns (id, is_new). An unresolved incident with the same service+pattern is updated, not duplicated."""
    with conn() as c:
        row = c.execute("SELECT id FROM incidents WHERE service=? AND template=? AND status!='resolved'",
                        (inc["service"], inc["template"])).fetchone()
        if row:
            c.execute("UPDATE incidents SET count=count+?, last_seen=?, severity=? WHERE id=?",
                      (inc["count"], inc["last_seen"], inc["severity"], row["id"]))
            return row["id"], False
        cur = c.execute("""INSERT INTO incidents(service,template,severity,count,first_seen,last_seen,samples,created)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (inc["service"], inc["template"], inc["severity"], inc["count"], inc["first_seen"],
                         inc["last_seen"], "\n".join(inc["samples"]), datetime.now().isoformat(timespec="seconds")))
        return cur.lastrowid, True


def set_rca(i, cause, fix, source):
    with conn() as c:
        c.execute("UPDATE incidents SET root_cause=?, fix=?, rca_source=? WHERE id=?", (cause, fix, source, i))


def set_status(i, status):
    if status in ("open", "acknowledged", "resolved"):
        with conn() as c:
            c.execute("UPDATE incidents SET status=? WHERE id=?", (status, i))


def get(i):
    with conn() as c:
        r = c.execute("SELECT * FROM incidents WHERE id=?", (i,)).fetchone()
        return dict(r) if r else None


def list_incidents(status=None):
    q, args = "SELECT * FROM incidents", ()
    if status:
        q, args = q + " WHERE status=?", (status,)
    with conn() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY severity, count DESC", args)]
