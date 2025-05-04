FROM python:3-slim

ENV REDIRECT_TO https://duckduckgo.com

EXPOSE 8080

WORKDIR /var/www/

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py gunicorn_config.py .

CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
