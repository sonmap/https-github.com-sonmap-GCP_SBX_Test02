FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
COPY sandbox-request.schema.json .
RUN useradd --system --uid 10001 appuser
USER appuser
CMD exec gunicorn --bind :${PORT:-8080} --workers 2 --threads 8 --timeout 0 main:app
