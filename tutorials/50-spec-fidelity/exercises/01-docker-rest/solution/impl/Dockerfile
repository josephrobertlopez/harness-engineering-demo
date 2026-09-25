FROM python:3.12-slim

# Stdlib only (PRD-8): no pip install, so nothing to pin, patch or audit.
WORKDIR /app
COPY app.py rates.json ./

RUN useradd --system --uid 10001 --no-create-home fx
USER fx

ENV PORT=8080
EXPOSE 8080

CMD ["python", "app.py"]
