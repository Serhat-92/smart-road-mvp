FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY services/gateway-api/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY shared /app/shared
COPY services/gateway-api /app/services/gateway-api
COPY infra /app/infra

COPY services/gateway-api/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

WORKDIR /app/services/gateway-api

EXPOSE 8080

CMD ["/app/entrypoint.sh"]
