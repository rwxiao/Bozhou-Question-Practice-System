FROM node:22-slim AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN python -c "from pathlib import Path; p=Path('requirements.txt'); Path('requirements.runtime.txt').write_text(''.join(line for line in p.read_text().splitlines(keepends=True) if not line.startswith(('pytest==', 'mypy=='))))" \
    && pip install --no-cache-dir -r requirements.runtime.txt
COPY app.py .
COPY --from=ui /web/build ./web/build
COPY ops ./ops
RUN useradd --uid 10001 --create-home practice && mkdir /data /backups && chown practice:practice /data /backups
USER practice
ENV DATABASE=/data/practice.db
EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000","--proxy-headers","--forwarded-allow-ips=*"]
