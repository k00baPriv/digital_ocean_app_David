FROM python:3-slim

ENV TRADING_VIEW_FIELD_ID=${TRADING_VIEW_FIELD_ID}

EXPOSE 8080

WORKDIR /var/www/

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y vim

COPY app.py gunicorn_config.py .

CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
