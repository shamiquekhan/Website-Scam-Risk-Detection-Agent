# PROMPTS.md

All LLM prompts used in the system, versioned. The summarizer is the only place an LLM is called - keep it that way (see `AGENTS.md` invariant #1). If you add a second LLM call anywhere, document it here too.

---

## Summarizer prompt (v1)

**Used in:** `backend/app/llm/summarizer.py`
**Model:** Groq - small/fast model (e.g. Llama 3.1 8B) for low latency
**Input:** structured signal list + final score + final verdict (all already computed - the LLM receives facts, not raw data to interpret)
**Output:** 2-4 plain-English sentences

### System prompt
```
You are summarizing a website risk scan for a non-technical reader.

You will be given:
- A final risk score (0-100) and verdict (Safe / Caution / High Risk) that have ALREADY been calculated by a rule-based system.
- A list of specific findings that produced that score.

Your job is ONLY to summarize these given findings in plain English, in 2-4 sentences.

Strict rules:
- Do NOT invent, assume, or add any risk or safety claim not present in the findings given to you.
- Do NOT change, soften, or contradict the verdict provided.
- Do NOT give the user instructions or advice beyond what the findings support (no "you should never..." unless a finding directly supports it).
- Write for someone with no technical background - avoid jargon like "ASN" or "RDAP"; say "hosting provider" or "domain registration records" instead.
- If the verdict is Safe, keep the tone reassuring but not absolute (avoid "100% safe" - use "no red flags were found").
- If most signals were unavailable, mention that the check was limited rather than presenting false confidence.
```

### User prompt template
```
Score: {score}/100
Verdict: {verdict}

Findings:
{for each signal where available=True and passed=False}
- [{category}] {detail}
{end for}

{if no failed signals}
No red flags were found across all checks performed.
{end if}

{if signals_unavailable_count > threshold}
Note: {signals_unavailable_count} of {total_signals} checks could not be completed.
{end if}

Write the 2-4 sentence summary now.
```

### Fallback (if Groq call fails or times out)
Template-string fallback, no LLM involved:
```python
def fallback_summary(score: int, verdict: str, failed_signals: list[SignalResult]) -> str:
    if not failed_signals:
        return f"This site scored {score}/100 ({verdict}). No red flags were found across all checks performed."
    reasons = "; ".join(s.detail for s in failed_signals[:3])
    return f"This site scored {score}/100 ({verdict}). Key concerns: {reasons}."
```

### Testing this prompt
Manually run against three fixture sets (all-clear / mixed / high-risk - see `docs/implementation-plan.md` §5) and read the output for:
1. Does it stay faithful to only the given findings? (no invented risks)
2. Does the tone match the verdict? (Caution shouldn't sound as alarming as High Risk, or as reassuring as Safe)
3. Is it actually readable by someone non-technical? (read it out loud test)

Log any drift as a prompt revision (bump to v2 with a changelog note below), not a one-off ignored quirk.

---

## Changelog

- **v1** - initial version, strict summary-only constraint, fallback template added after initial design (never shipped without a fallback path).
