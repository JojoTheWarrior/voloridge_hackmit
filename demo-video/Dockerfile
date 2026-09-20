FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir Pillow==12.3.0 numpy==2.5.3 fonttools[woff]==4.63.0 ruff==0.15.7
WORKDIR /film
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["python", "render.py", "--preview"]
