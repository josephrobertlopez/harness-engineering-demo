FROM python:3.12-slim

WORKDIR /app

# Copy application files
COPY app.py .
COPY rates.json .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

USER appuser

# Set default port (can be overridden with PORT environment variable)
ENV PORT=8080

EXPOSE 8080

# Run the service
CMD ["python", "app.py"]
