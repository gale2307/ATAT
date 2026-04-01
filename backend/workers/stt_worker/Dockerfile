FROM runpod/base:0.6.2-cuda12.1.0

RUN pip install --no-cache-dir faster-whisper runpod

WORKDIR /app
COPY handler.py .

CMD ["python", "-u", "handler.py"]
