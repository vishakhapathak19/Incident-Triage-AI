"""Parse logs -> engineer features -> Isolation Forest -> cluster into incidents with severity."""
import re
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

LINE = re.compile(r"^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})\s+(DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\s+(\S+)\s+(.*)$")
LEVEL = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3, "CRITICAL": 4, "FATAL": 4}
KEYWORDS = ["timeout", "refused", "exception", "failed", "unauthorized", "denied",
            "out of memory", "unavailable", "deadlock", "crash", "traceback"]
COLS = ["ts", "level", "service", "message"]


def parse_lines(lines):
    """Parse 'YYYY-MM-DD HH:MM:SS LEVEL service message'. Non-matching lines (stack traces) join the previous entry."""
    rows = []
    for raw in lines:
        raw = raw.rstrip("\n")
        m = LINE.match(raw)
        if m:
            ts, lvl, svc, msg = m.groups()
            rows.append({"ts": ts.replace("T", " "), "level": "WARN" if lvl == "WARNING" else lvl,
                         "service": svc, "message": msg})
        elif rows and raw.strip():
            rows[-1]["message"] += " | " + raw.strip()
    df = pd.DataFrame(rows, columns=COLS)
    df["ts"] = pd.to_datetime(df["ts"])
    df["template"] = df["message"].map(to_template)
    return df


def to_template(msg):
    """Collapse variable parts (numbers, IPs, hex) so similar errors group together."""
    head = msg.split(" | ")[0]
    return re.sub(r"0x[0-9a-fA-F]+|(?<![A-Za-z_])\d+(?:\.\d+)*", "<*>", head)


def build_features(df):
    f = pd.DataFrame(index=df.index)
    f["level"] = df["level"].map(LEVEL).fillna(1)
    f["length"] = df["message"].str.len()
    low = df["message"].str.lower()
    f["keywords"] = sum(low.str.contains(k, regex=False).astype(int) for k in KEYWORDS)
    freq = df.groupby("template")["template"].transform("count")
    f["rarity"] = -np.log(freq / len(df))
    minute = df["ts"].dt.floor("min")
    f["burst"] = df["level"].isin(["ERROR", "CRITICAL", "FATAL"]).astype(int).groupby(minute).transform("sum")
    return f


def detect(df, contamination=0.1):
    """Flag anomalies with Isolation Forest; CRITICAL/FATAL entries are always flagged."""
    df = df.copy()
    if len(df) < 10:
        df["anomaly"] = df["level"].map(LEVEL) >= 3
        df["score"] = 0.0
        return df
    X = StandardScaler().fit_transform(build_features(df))
    model = IsolationForest(contamination=contamination, random_state=42).fit(X)
    df["score"] = -model.score_samples(X)
    df["anomaly"] = model.predict(X) == -1
    df.loc[df["level"].isin(["CRITICAL", "FATAL"]), "anomaly"] = True
    return df


def severity(max_level, count, text):
    low = text.lower()
    if max_level >= 4 or any(k in low for k in ("out of memory", "unavailable", "outage", "data loss")) \
            or (max_level >= 3 and count >= 10):
        return "P1"
    return {3: "P2", 2: "P3"}.get(max_level, "P4")


def build_incidents(df):
    """Group anomalies by (service, template) into incidents with severity."""
    out = []
    lvl = df["level"].map(LEVEL)
    has_kw = df["message"].str.lower().apply(lambda m: any(k in m for k in KEYWORDS))
    actionable = df["anomaly"] & ((lvl >= 3) | ((lvl == 2) & has_kw))  # ignore anomalous-but-harmless INFO/DEBUG
    for (svc, tpl), g in df[actionable].groupby(["service", "template"]):
        max_level = int(g["level"].map(LEVEL).max())
        samples = g["message"].head(3).tolist()
        out.append({
            "service": svc, "template": tpl, "count": int(len(g)),
            "first_seen": g["ts"].min().isoformat(), "last_seen": g["ts"].max().isoformat(),
            "severity": severity(max_level, len(g), " ".join(samples)), "samples": samples,
        })
    return sorted(out, key=lambda i: (i["severity"], -i["count"]))
