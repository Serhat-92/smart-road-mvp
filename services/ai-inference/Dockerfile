FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/services/ai-inference:/app/services/ai-inference/src \
    EASYOCR_MODULE_PATH=/app/.EasyOCR

WORKDIR /app

COPY services/ai-inference/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY yolov8n.pt /app/yolov8n.pt
COPY services/ai-inference /app/services/ai-inference

WORKDIR /app/services/ai-inference

EXPOSE 8090

CMD ["python", "service_api.py"]
