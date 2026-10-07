FROM python:3.12-slim

# Optional heavy extras, off by default:
#   --build-arg INSTALL_LIBREOFFICE=1   page-count check of certified documents (+ Carlito, metric-compatible with Calibri)
#   --build-arg INSTALL_TESSERACT=1     offline OCR (Arabic, French, English)
ARG INSTALL_LIBREOFFICE=0
ARG INSTALL_TESSERACT=0
RUN set -eux; apt-get update; \
    if [ "$INSTALL_LIBREOFFICE" = "1" ]; then apt-get install -y --no-install-recommends libreoffice-writer fonts-crosextra-carlito; fi; \
    if [ "$INSTALL_TESSERACT" = "1" ]; then apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra tesseract-ocr-eng; fi; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY aminos ./aminos
RUN pip install --no-cache-dir ".[llm,docx,xlsx,pdf,web,chroma]" \
    && if [ "$INSTALL_TESSERACT" = "1" ]; then pip install --no-cache-dir ".[ocr]"; fi
COPY app.py ./

# Persistent data (memory, registry, archive, HMAC key) lives in /data, outside the image.
RUN useradd --create-home --uid 10001 aminos && mkdir /data && chown aminos /data
USER aminos
WORKDIR /data
ENV PYTHONUNBUFFERED=1 STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true STREAMLIT_SERVER_ADDRESS=0.0.0.0 STREAMLIT_SERVER_PORT=8501
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4)"
CMD ["streamlit", "run", "/app/app.py"]
