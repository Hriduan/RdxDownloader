FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=8080 RDX_DATA_DIR=/tmp/rdxdownloader DENO_DIR=/tmp/rdx-deno-cache DENO_NO_UPDATE_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/* && useradd --create-home --uid 10001 rdx
WORKDIR /app
COPY requirements.txt requirements-docker.txt ./
RUN pip install --no-cache-dir -r requirements-docker.txt
COPY --chown=rdx:rdx . .
USER rdx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=3)" || exit 1
CMD ["python", "-m", "server.app"]
