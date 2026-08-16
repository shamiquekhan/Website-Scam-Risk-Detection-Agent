import os

import httpx

from app.models import ScanResult

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")
OLLAMA_TIMEOUT = 20

SYSTEM_PROMPT = (
    "You are summarizing a website risk scan for a non-technical reader.\n\n"
    "You will be given:\n"
    "- A final risk score (0-100, or 'insufficient data') and verdict that have ALREADY been calculated by a rule-based system.\n"
    "- A list of specific findings, marking each check as passed, red flag, or unavailable.\n\n"
    "Your job is ONLY to summarize the given findings in plain English, in 2-4 sentences.\n\n"
    "Strict rules:\n"
    "- Do NOT invent, assume, or add any risk or safety claim not present in the findings given to you.\n"
    "- Do NOT change, soften, or contradict the verdict provided.\n"
    "- If the verdict is 'Insufficient Data', do NOT imply or reassure that the site is safe. Make the lack of available checks the headline, and state that the few checks that ran do not count for much without reputation/hosting data.\n"
    "- Do NOT give the user instructions or advice beyond what the findings support.\n"
    "- Write for someone with no technical background - avoid jargon like 'ASN' or 'RDAP'.\n"
    "- If the verdict is Safe, keep the tone reassuring but not absolute.\n"
    "- If most signals were unavailable, mention that the check was limited."
)


def fallback_summary(scan_result: ScanResult) -> str:
    if scan_result.verdict == "Insufficient Data":
        return insufficient_summary(scan_result)

    failed = [s for s in scan_result.signals if not s.passed and s.available]
    score_text = f"scored {scan_result.score}/100 ({scan_result.verdict})"
    if not failed:
        return f"This site {score_text}. No red flags were found across all checks performed."
    reasons = "; ".join(s.detail for s in failed[:3])
    return f"This site {score_text}. Key concerns: {reasons}."


def insufficient_summary(scan_result: ScanResult) -> str:
    completed = scan_result.completed_signals
    total = scan_result.total_signals
    passed = [s.signal_name for s in scan_result.signals if s.available and s.passed]
    body = (
        f"Only {completed} of {total} checks completed ({scan_result.confidence}% confidence), so "
        "this site could not be properly assessed."
    )
    if passed:
        body += (
            f" The checks that ran ({', '.join(passed)}) showed no red flags, but no third-party "
            "reputation or hosting data was run, so a clean result is not meaningful."
        )
    else:
        body += " None of the checks that ran produced usable risk data."
    body += (
        " Treat the site as unverified, and do not enter payment or personal details until it can "
        "be checked against reputation sources."
    )
    return body


def _build_prompt(scan_result: ScanResult) -> str:
    unavailable_count = sum(1 for s in scan_result.signals if not s.available)
    total_signals = len(scan_result.signals)

    findings_lines = []
    for signal in scan_result.signals:
        if signal.available:
            status = "red flag" if not signal.passed else "passed"
            findings_lines.append(f"- [{signal.category}] {status}: {signal.detail}")
        else:
            findings_lines.append(f"- [{signal.category}] unavailable: {signal.detail}")
    findings_text = "\n".join(findings_lines)

    unavailable_note = ""
    if unavailable_count > 0:
        unavailable_note = f"\nNote: {unavailable_count} of {total_signals} checks could not be completed."

    score_text = (
        "No score (insufficient data)" if scan_result.score is None else f"{scan_result.score}/100"
    )
    return (
        f"Score: {score_text}\n"
        f"Verdict: {scan_result.verdict}\n"
        f"Confidence: {scan_result.confidence}% ({scan_result.completed_signals} of {scan_result.total_signals} checks completed)\n\n"
        f"Findings:\n{findings_text}\n"
        f"{unavailable_note}\n\n"
        "Write the 2-4 sentence summary now."
    )


async def _ollama_summarize(prompt: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 250},
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return (data.get("response") or "").strip() or None
    except Exception:
        return None


def _groq_summarize(prompt: str) -> str | None:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None
    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            model="llama3-8b-8192",
            max_tokens=250,
            temperature=0.3,
        )
        summary = chat_completion.choices[0].message.content.strip()
        return summary or None
    except Exception:
        return None


async def summarize(scan_result: ScanResult) -> str:
    prompt = _build_prompt(scan_result)

    summary = await _ollama_summarize(prompt)
    if summary:
        return summary

    summary = await asyncio_groq_wrapper(_groq_summarize, prompt)
    if summary:
        return summary

    return fallback_summary(scan_result)


async def asyncio_groq_wrapper(func, prompt: str) -> str | None:
    import asyncio

    return await asyncio.to_thread(func, prompt)