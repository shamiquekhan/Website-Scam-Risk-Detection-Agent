import asyncio
import os
import sys
import threading

import streamlit as st

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.models import to_dict  # noqa: E402
from app.orchestrator import run_scan  # noqa: E402

VERDICT_STYLE = {
    "Safe": ("#34d399", "#065f46"),
    "Likely Safe": ("#a3e635", "#3f6212"),
    "Caution": ("#fbbf24", "#92400e"),
    "Suspicious": ("#fb923c", "#9a3412"),
    "High Risk": ("#f87171", "#7f1d1d"),
    "Insufficient Data": ("#94a3b8", "#334155"),
}

SIGNAL_LABELS = {
    "ssl_check": "SSL Certificate",
    "whois_check": "Domain Age & WHOIS",
    "dns_hosting": "DNS & Hosting",
    "safe_browsing": "Google Safe Browsing",
    "virustotal": "VirusTotal",
    "urlhaus": "URLhaus Blocklist",
    "openphish": "OpenPhish Feed",
    "local_ml": "Local ML Classifier",
    "domain_lexical": "URL Structure",
    "content_heuristics": "Page Content",
    "typosquat": "Brand Impersonation",
}


def run_async(coro):
    """Run an async coroutine, tolerating an already-running event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result = {}

    def _target():
        result["value"] = asyncio.run(coro)

    thread = threading.Thread(target=_target)
    thread.start()
    thread.join()
    return result["value"]


def scan_url(url: str) -> dict:
    return to_dict(run_async(run_scan(url)))


scan_cached = st.cache_data(ttl=86400, show_spinner=False)(scan_url)


def verdict_badge(verdict: str) -> None:
    fg, bg = VERDICT_STYLE.get(verdict, ("#94a3b8", "#334155"))
    st.markdown(
        f"<span style='background:{bg};color:{fg};padding:4px 14px;border-radius:999px;"
        f"font-weight:600;font-size:1.05rem'>{verdict}</span>",
        unsafe_allow_html=True,
    )


def display_result(result: dict) -> None:
    score = result["score"]
    verdict = result["verdict"]
    st.subheader("Risk assessment")
    col_score, col_meta = st.columns([1, 2])
    with col_score:
        if score is None:
            st.markdown(
                "<div style='font-size:3rem;font-weight:700;color:#94a3b8'>-</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='font-size:3rem;font-weight:700;color:#22d3ee'>{score}/100</div>",
                unsafe_allow_html=True,
            )
    with col_meta:
        verdict_badge(verdict)
        st.caption(
            f"{result['completed_signals']} of {result['total_signals']} checks completed - "
            f"{result['confidence']}% confidence"
        )
        if result["cached"]:
            st.caption("Cached result (scanned within the last 24h).")

    if score is not None:
        st.progress(score / 100, text="Safety score")

    st.caption(result["url"])
    if result["summary"]:
        st.info(result["summary"])

    st.subheader("Signal breakdown")
    for signal in result["signals"]:
        label = SIGNAL_LABELS.get(signal["signal_name"], signal["signal_name"])
        if not signal["available"]:
            icon, tone = "-", "secondary"
        elif signal["passed"]:
            icon, tone = "OK", "success"
        else:
            icon, tone = "FAIL", "error"

        if tone == "success":
            st.success(f"{icon} **{label}** - {signal['detail']}")
        elif tone == "error":
            st.error(f"{icon} **{label}** ( -{signal['deduction']} pts ) - {signal['detail']}")
        else:
            st.caption(f"{icon} {label} - {signal['detail']}")


def single_scan_tab() -> None:
    st.markdown(
        "Zero-cost, multi-signal scanner: SSL, domain age, DNS, content heuristics, "
        "typosquatting, OpenPhish feed, URLhaus blocklist, and a local on-device ML "
        "phishing classifier. No API keys required."
    )
    url = st.text_input("Enter a URL", placeholder="https://example.com")
    if st.button("Scan", type="primary", disabled=not url.strip()):
        with st.spinner("Running 11 independent checks..."):
            try:
                result = scan_cached(url.strip())
            except Exception as exc:  # noqa: BLE001
                st.error(f"Scan failed: {exc}")
                return
        display_result(result)


def parse_urls(text: str) -> list[str]:
    urls = [line.strip() for line in text.replace(",", "\n").splitlines() if line.strip()]
    return urls[:100]


def batch_scan_tab() -> None:
    st.markdown("Paste up to 100 URLs (one per line or comma-separated).")
    text = st.text_area("URLs", placeholder="https://example.com\nhttps://secure-login-example.tk/login")
    uploaded = st.file_uploader("...or upload a CSV (URLs in the first column)", type=["csv", "txt"])

    urls = parse_urls(text)
    if uploaded is not None:
        content = uploaded.getvalue().decode("utf-8", errors="replace")
        for line in content.splitlines():
            first = line.split(",")[0].strip()
            if first and not first.startswith(("#", "url", "URL", "domain", "Domain")):
                if first not in urls and len(urls) < 100:
                    urls.append(first)

    if st.button("Scan batch", type="primary", disabled=not urls):
        rows = []
        progress = st.progress(0.0, text="Scanning...")
        for i, url in enumerate(urls):
            try:
                result = scan_cached(url)
                rows.append(
                    {
                        "URL": result["url"],
                        "Score": result["score"],
                        "Verdict": result["verdict"],
                        "Confidence": f"{result['confidence']}%",
                    }
                )
            except Exception as exc:  # noqa: BLE001
                rows.append({"URL": url, "Score": None, "Verdict": "Error", "Confidence": str(exc)})
            progress.progress((i + 1) / len(urls), text=f"Scanning {i + 1}/{len(urls)}")
        progress.empty()
        st.dataframe(rows, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="ScamShield AI", layout="centered")
    st.title("ScamShield AI")
    st.caption("Website Scam Risk Detector Agent - free, open-source, no API keys.")
    st.divider()

    tab_single, tab_batch = st.tabs(["Single scan", "Batch scan"])
    with tab_single:
        single_scan_tab()
    with tab_batch:
        batch_scan_tab()


if __name__ == "__main__":
    main()