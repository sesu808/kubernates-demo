FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN pip install nonexistentpackage123    # ← fake package that doesn't exist
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]s