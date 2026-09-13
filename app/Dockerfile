FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=80
EXPOSE 80

# Gunicorn in production; app.py's __main__ block (dev server) is not used here.
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:80", "app:app"]
