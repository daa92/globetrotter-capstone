FROM python:3.11-slim

WORKDIR /globetrotter

# Install only production dependencies — pytest/locust never ship in this image.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY data/destinations.json ./data/destinations.json

# Run as a non-root user
RUN useradd --create-home appuser

RUN mkdir -p /globetrotter/data && chown -R appuser:appuser /globetrotter/data

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
