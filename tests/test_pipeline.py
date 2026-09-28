import os
import tempfile

os.environ["INCIDENT_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
from core import pipeline, rca, store

LOGS = ["2026-09-28 10:00:0%d INFO web Request completed in %d ms" % (i % 10, i) for i in range(60)] + \
       ["2026-09-28 10:05:00 ERROR db Connection timeout after 30s",
        "2026-09-28 10:05:01 CRITICAL db Out of memory: killed process 42"]


def test_parse_and_template():
    df = pipeline.parse_lines(LOGS + ["  File x.py, line 1"])
    assert len(df) == 62 and "<*>" in df["template"].iloc[0]


def test_detects_critical_as_p1():
    inc = pipeline.build_incidents(pipeline.detect(pipeline.parse_lines(LOGS)))
    assert any(i["severity"] == "P1" and i["service"] == "db" for i in inc)


def test_rca_fallback_and_dedupe():
    inc = {"service": "db", "template": "t", "severity": "P2", "count": 2, "first_seen": "a",
           "last_seen": "b", "samples": ["Connection timeout"]}
    assert "slow or unreachable" in rca.rule_based(inc)[0]
    store.init()
    i, new1 = store.upsert(inc)
    j, new2 = store.upsert(inc)
    assert i == j and new1 and not new2
