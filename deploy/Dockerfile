FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# tesseract with Arabic, French, English, Dutch for offline OCR; git only to install the pinned agent-coordinator
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra tesseract-ocr-eng tesseract-ocr-nld git openssl curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY pyproject.toml README.md ./
COPY aminos ./aminos
RUN pip install ".[all,swarm,docx]" \
    && apt-get purge -y git && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
COPY app.py saas_app.py /app/

# Non-root; translation memory, ledger and uploads live in the /data volume (the app's default "tm.sqlite" lands there)
RUN useradd --create-home --uid 10001 aminos && mkdir /data && chown aminos /data
USER aminos
WORKDIR /data
VOLUME /data
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS "http://127.0.0.1:${PORT:-8501}/_stcore/health" || exit 1
# Multi-user app by default (AMINOS_APP=/app/app.py for the single-user page). Hosts such as Render inject $PORT.
ENV AMINOS_APP=/app/saas_app.py AMINOS_DATA_DIR=/data/saas
CMD ["sh", "-c", "exec streamlit run ${AMINOS_APP} --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true --browser.gatherUsageStats=false --server.maxUploadSize=50"]
