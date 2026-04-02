FROM runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04

RUN pip install --no-cache-dir faster-whisper runpod

WORKDIR /app
COPY handler.py .

CMD ["python", "-u", "handler.py"]
