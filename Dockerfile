FROM python:3-slim

ENV REDIRECT_TO https://duckduckgo.com

EXPOSE 8080

WORKDIR /var/www/

# Install required system packages
RUN apt-get update && apt-get install -y \
    openssl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY gunicorn_config.py .

# Create SSL certificates directory
RUN mkdir -p /etc/ssl/certs

CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
