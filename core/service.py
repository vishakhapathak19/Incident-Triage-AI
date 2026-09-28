"""Orchestrates the full flow; shared by the web app and the live monitor."""
from . import alerts, pipeline, rca, store


def process(lines):
    df = pipeline.detect(pipeline.parse_lines(lines))
    incidents = pipeline.build_incidents(df)
    new = 0
    for inc in incidents:
        i, is_new = store.upsert(inc)
        if is_new:
            new += 1
            cause, fix, src = rca.analyze(inc)
            store.set_rca(i, cause, fix, src)
            alerts.notify(i, inc, cause)
    return {"lines": len(df), "anomalies": int(df["anomaly"].sum()), "incidents": len(incidents), "new": new}


def report(inc):
    return f"""# Incident #{inc['id']} - RCA Report

- **Service:** {inc['service']}
- **Severity:** {inc['severity']}   **Status:** {inc['status']}
- **Pattern:** `{inc['template']}`
- **Occurrences:** {inc['count']}
- **First seen:** {inc['first_seen']}   **Last seen:** {inc['last_seen']}

## Sample log lines
```
{inc['samples']}
```

## Probable root cause ({inc['rca_source']})
{inc['root_cause']}

## Recommended fix
{inc['fix']}
"""
