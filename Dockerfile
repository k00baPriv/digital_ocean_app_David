FROM python:3-slim

# Define build arguments for non-sensitive data
ARG TRADING_VIEW_FIELD_ID
ARG REDIS_HOST
ARG REDIS_PORT
ARG REDIS_USERNAME

# Set environment variables from build arguments
ENV TRADING_VIEW_FIELD_ID=$TRADING_VIEW_FIELD_ID
ENV REDIS_HOST=$REDIS_HOST
ENV REDIS_PORT=$REDIS_PORT
ENV REDIS_USERNAME=$REDIS_USERNAME

# Handle sensitive data through runtime environment variables
ENV REDIS_PASSWORD=""

EXPOSE 8080

WORKDIR /var/www/

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y vim

COPY app.py gunicorn_config.py .

CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
