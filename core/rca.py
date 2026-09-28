"""Root-cause analysis: Generative AI (Claude API) with a rule-based fallback."""
import json
import os

KB = [
    (("out of memory", "oom"), "Process exhausted available memory (leak or undersized limits).",
     "Check memory graphs, restart the service, raise limits, and profile for leaks."),
    (("timeout", "timed out"), "Downstream dependency (DB/API) is slow or unreachable.",
     "Check dependency health and network, review connection pool size and timeout settings."),
    (("unauthorized", "denied", "forbidden"), "Invalid credentials/tokens or a possible brute-force attempt.",
     "Verify token expiry and permissions; check source IPs and block if suspicious."),
    (("refused", "unavailable"), "Target service is down or not listening.",
     "Check service status and recent deployments; restart or roll back."),
    (("deadlock",), "Concurrent transactions are locking each other.",
     "Inspect long-running queries and lock order; add retries."),
    (("exception", "traceback"), "Unhandled application error.",
     "Read the stack trace, reproduce with the failing input, and fix or add error handling."),
]


def rule_based(inc):
    text = (inc["template"] + " " + " ".join(inc["samples"])).lower()
    for keys, cause, fix in KB:
        if any(k in text for k in keys):
            return cause, fix
    return "Unusual pattern detected; cause unknown.", "Review surrounding logs and recent changes."


def llm_based(inc):
    import anthropic
    prompt = (f"You are an application support engineer. Service: {inc['service']}. "
              f"Occurrences: {inc['count']}. Sample log lines:\n" + "\n".join(inc["samples"]) +
              '\n\nReply ONLY with JSON: {"root_cause": "...", "fix": "..."} (one sentence each).')
    msg = anthropic.Anthropic().messages.create(
        model=os.getenv("LLM_MODEL", "claude-sonnet-5"), max_tokens=300,
        messages=[{"role": "user", "content": prompt}])
    data = json.loads(msg.content[0].text.strip().strip("`").removeprefix("json").strip())
    return data["root_cause"], data["fix"]


def analyze(inc):
    """Returns (root_cause, fix, source). Falls back to rules if no API key or the call fails."""
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return (*llm_based(inc), "llm")
        except Exception:
            pass
    return (*rule_based(inc), "rules")
