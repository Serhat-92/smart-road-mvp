FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY apps/command-center/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY apps/command-center /app/apps/command-center

WORKDIR /app/apps/command-center

EXPOSE 8000

CMD ["python", "server.py"]
