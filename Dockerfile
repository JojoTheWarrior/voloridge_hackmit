FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 KINGDOM_FAKE_DEVIN=1
EXPOSE 8030
CMD ["python", "main.py", "serve", "--host", "0.0.0.0", "--db", "/state/kingdom.db"]
