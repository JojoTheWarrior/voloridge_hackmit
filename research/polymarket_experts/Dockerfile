FROM python:3.12-slim
WORKDIR /work
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ENV MPLCONFIGDIR=/work/.cache/matplotlib PYTHONDONTWRITEBYTECODE=1
CMD ["python", "scripts/run.py"]
