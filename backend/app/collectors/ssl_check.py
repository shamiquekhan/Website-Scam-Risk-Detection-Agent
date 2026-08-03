import ssl
import socket
import subprocess
from datetime import datetime, timezone
from app.models import SignalResult


async def check(domain_or_url: str) -> SignalResult:
    host = domain_or_url.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                if cert:
                    return _process_cert(cert)
    except ssl.SSLCertVerificationError as exc:
        return SignalResult(
            signal_name="ssl_check",
            category="ssl",
            passed=False,
            deduction=20,
            detail=f"SSL certificate could not be verified ({exc.verify_message}).",
            raw_data={"verification_error": exc.verify_message},
        )
    except Exception:
        return SignalResult(
            signal_name="ssl_check",
            category="ssl",
            passed=False,
            deduction=20,
            detail="Site does not support HTTPS or connection was refused — no encryption for any data you enter.",
        )


def _openssl_get_not_after(pem: str) -> str:
    try:
        result = subprocess.run(
            ["openssl", "x509", "-noout", "-enddate"],
            input=pem.encode(),
            capture_output=True,
            timeout=5,
        )
        for line in result.stdout.decode().split("\n"):
            if line.startswith("notAfter="):
                return line.split("=", 1)[1].strip()
    except Exception:
        return ""
    return ""


def _process_cert(cert: dict) -> SignalResult:
    not_after_str = cert.get("notAfter", "")
    if not not_after_str:
        return SignalResult(
            signal_name="ssl_check",
            category="ssl",
            passed=True,
            deduction=0,
            detail="SSL certificate is valid (expiry date unknown).",
            raw_data={"issuer": dict(x[0] for x in cert.get("issuer", []) if x)},
        )
    return _score_from_expiry(not_after_str, cert)


def _score_from_expiry(not_after_str: str, cert_or_host) -> SignalResult:
    try:
        expiry = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            expiry = datetime.strptime(not_after_str, "%Y-%m-%d %H:%M:%S %Z").replace(tzinfo=timezone.utc)
        except ValueError:
            expiry = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    days_left = (expiry - now).days

    if days_left <= 0:
        return SignalResult(
            signal_name="ssl_check",
            category="ssl",
            passed=False,
            deduction=15,
            detail=f"SSL certificate expired {abs(days_left)} days ago.",
            raw_data={"expiry": not_after_str},
        )

    if days_left <= 7:
        return SignalResult(
            signal_name="ssl_check",
            category="ssl",
            passed=False,
            deduction=5,
            detail=f"SSL certificate expires in {days_left} days — renewal needed soon.",
            raw_data={"expiry": not_after_str},
        )

    issuer = {}
    if isinstance(cert_or_host, dict):
        issuer = dict(x[0] for x in cert_or_host.get("issuer", []) if x)

    return SignalResult(
        signal_name="ssl_check",
        category="ssl",
        passed=True,
        deduction=0,
        detail=f"SSL certificate is valid, expires in {days_left} days.",
        raw_data={"issuer": issuer, "expiry": not_after_str},
    )
