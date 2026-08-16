FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-seed the free threat feeds so the first scans work offline.
RUN mkdir -p data && \
    (curl -fsSL -m 60 -o data/openphish_feed.txt https://openphish.com/feed.txt || true) && \
    (curl -fsSL -m 120 -o data/urlhaus_blocklist.txt https://urlhaus.abuse.ch/downloads/text_online/ || true)

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]