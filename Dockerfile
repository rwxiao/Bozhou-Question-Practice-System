FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY web ./web
COPY ops ./ops
RUN useradd --uid 10001 --create-home practice && mkdir /data /backups && chown practice:practice /data /backups
USER practice
ENV DATABASE=/data/practice.db
EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000","--proxy-headers","--forwarded-allow-ips=*"]
