FROM python:3.12-slim

# Stdlib only (PRD-8): no pip install, so nothing to pin, patch or audit.
WORKDIR /app
COPY app.py rates.json ./

RUN useradd --system --uid 10001 --no-create-home fx
USER fx

ENV PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8080') + '/healthz', timeout=2)"]

CMD ["python", "app.py"]
