#!/usr/bin/env python3
"""RdxDownloader v1: single-process bounded backend + static frontend.
Run behind an HTTPS reverse proxy with a request-size limit and an outbound firewall.
No authentication/cookies for upstream platforms; no cloud or provider API keys needed.
"""
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import mimetypes
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import tempfile
import time
from urllib.parse import unquote, urlsplit

if __package__:
    from .network import validate_url
    from .runtime import dependency_status
    from .platforms import normalize_url, platform_for, PLATFORMS
else:
    from network import validate_url
    from runtime import dependency_status
    from platforms import normalize_url, platform_for, PLATFORMS

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('RDX_DATA_DIR', str(Path(tempfile.gettempdir())/'rdxdownloader'))).resolve()
PORT = int(os.environ.get('PORT', '8080'))
HOST = os.environ.get('HOST', '127.0.0.1')
MAX_BYTES = int(os.environ.get('RDX_MAX_FILE_MB', '512')) * 1024 * 1024
MAX_DURATION = int(os.environ.get('RDX_MAX_DURATION_SECONDS', '1800'))
MAX_RUNTIME = int(os.environ.get('RDX_MAX_JOB_SECONDS', '1200'))
WORKERS = max(1, min(4, int(os.environ.get('RDX_MAX_WORKERS', '2'))))
TTL = 3600
ORIGINS = {v.strip().rstrip('/') for v in os.environ.get('RDX_ALLOWED_ORIGINS', '').split(',') if v.strip()}
# Keep the capability store in memory. Use one process/one replica; restarts expire links.
inspections, jobs, rate_log = {}, {}, defaultdict(deque)
lock = threading.RLock()
worker_slots = threading.BoundedSemaphore(WORKERS)
executor = ThreadPoolExecutor(max_workers=WORKERS)


class APIError(Exception):
    def __init__(self, message, status=400, code=None):
        self.message, self.status, self.code = message, status, code


def settings_ready():
    return dependency_status()['downloadsReady']


def run_worker(payload, deadline, on_event=None, directory=None):
    proc = subprocess.Popen([sys.executable, str(ROOT / 'server/worker.py')], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                            start_new_session=True, env={**os.environ, 'PYTHONUNBUFFERED': '1'})
    events = deque(maxlen=300)
    result = [None]

    def reader():
        for line in proc.stdout:
            if len(line) > 2_000_000:
                continue
            try:
                event = json.loads(line)
                events.append(event)
                if 'ok' in event:
                    result[0] = event
                if on_event:
                    on_event(event)
            except (ValueError, TypeError):
                continue
    try:
        proc.stdin.write(json.dumps(payload))
        proc.stdin.close()
        t = threading.Thread(target=reader, daemon=True)
        t.start()
        started = time.monotonic()
        while proc.poll() is None:
            if time.monotonic() - started > deadline:
                raise APIError('The source took too long. Try a smaller format or another supported link.', 504)
            if directory:
                size = sum(p.stat().st_size for p in directory.glob('*') if p.is_file())
                if size > MAX_BYTES * 2 + 32 * 1024 * 1024:
                    raise APIError('This job exceeded the temporary disk limit.', 413)
            time.sleep(.2)
        t.join(timeout=3)
        output = result[0]
        if not output or not output.get('ok'):
            raise APIError((output or {}).get('error', 'The source could not be processed.'), 422, (output or {}).get('code'))
        return output
    finally:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=4)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        proc.stdout.close()


def inspect(url):
    url = normalize_url(url)
    validate_url(url, resolve=False)  # DNS resolution is bounded inside the worker timeout.
    if not worker_slots.acquire(blocking=False):
        raise APIError('The server is busy. Please try again in a moment.', 429)
    try:
        result = run_worker({'operation': 'inspect', 'url': url, 'maxDuration': MAX_DURATION}, 65)
    finally:
        worker_slots.release()
    token = secrets.token_urlsafe(24)
    with lock:
        if len(inspections) >= 200:
            oldest = min(inspections, key=lambda k: inspections[k]['created'])
            del inspections[oldest]
        inspections[token] = {'created': time.time(), 'url': url, 'result': result}
    public = {k: v for k, v in result.items() if k not in ('ok', 'formats')}
    public['inspection'] = token
    public['sourceFamily'] = platform_for(url)['id']
    public['sourceNote'] = platform_for(url)['note']
    public['formats'] = [{k: v for k, v in f.items() if k not in ('rawId', 'audioId')} for f in result['formats']]
    return public


def process_job(job_id, record, selected):
    directory = DATA / job_id
    acquired = False
    try:
        with worker_slots:
            acquired = True
            with lock:
                jobs[job_id]['status'] = 'processing'
            directory.mkdir(parents=True, exist_ok=False)
            def event(e):
                if 'progress' in e:
                    with lock:
                        if job_id in jobs:
                            jobs[job_id].update(progress=e['progress'], detail=e.get('detail', 'Preparing file.'))
            result = run_worker({'operation': 'download', 'url': record['url'], 'selected': selected,
                                 'directory': str(directory), 'maxBytes': MAX_BYTES, 'maxDuration': MAX_DURATION,
                                 'rateBytes': int(os.environ.get('RDX_RATE_BYTES', '4194304'))},
                                MAX_RUNTIME, on_event=event, directory=directory)
            file = (directory / result['file']).resolve()
            if file.parent != directory.resolve() or not file.is_file():
                raise APIError('Prepared file validation failed.')
            with lock:
                jobs[job_id].update(status='ready', progress=100, detail='Ready. This link expires after one hour.',
                                    file=str(file), name='RdxDownloader-' + job_id[:8] + file.suffix)
    except Exception as e:
        with lock:
            if job_id in jobs:
                jobs[job_id].update(status='error', error=e.message if isinstance(e, APIError) else 'The download could not be prepared.', code=e.code if isinstance(e, APIError) else None)
        shutil.rmtree(directory, ignore_errors=True)


def create_job(data):
    if not settings_ready():
        raise APIError('The host must install yt-dlp, FFmpeg and ffprobe before downloads are available.', 503)
    with lock:
        record = inspections.get(data.get('inspection'))
        if not record or time.time() - record['created'] > 1200:
            raise APIError('This format list expired. Inspect your link again.', 410)
        selected = next((f for f in record['result']['formats'] if f['id'] == data.get('format')), None)
        if selected is None:
            raise APIError('Choose an available format from the current list.')
        if selected.get('size') and selected['size'] > MAX_BYTES:
            raise APIError('This format exceeds the host file-size limit. Choose a smaller one.', 413)
        if sum(j['status'] in ('queued', 'processing') for j in jobs.values()) >= WORKERS * 2 or len(jobs) >= 100:
            raise APIError('The download queue is full. Please try again later.', 429)
        if shutil.disk_usage(DATA).free < MAX_BYTES * 3:
            raise APIError('The server needs more free disk space. Please try again later.', 503)
        token = secrets.token_urlsafe(24)
        jobs[token] = {'created': time.time(), 'status': 'queued', 'progress': 0, 'detail': 'Waiting for an available worker.'}
        executor.submit(process_job, token, record, selected)
    return {'id': token}


def cleanup():
    while True:
        now = time.time()
        with lock:
            for key in list(inspections):
                if now - inspections[key]['created'] > 1200:
                    del inspections[key]
            for key in list(jobs):
                if now - jobs[key]['created'] > TTL and jobs[key]['status'] not in ('queued', 'processing'):
                    del jobs[key]
                    shutil.rmtree(DATA / key, ignore_errors=True)
            for ip in list(rate_log):
                if not rate_log[ip] or now - rate_log[ip][-1] > 120:
                    del rate_log[ip]
        # Remove abandoned jobs after a restart. Active jobs are never removed.
        if DATA.exists():
            for p in DATA.iterdir():
                if p.is_dir() and p.name not in jobs and now - p.stat().st_mtime > TTL:
                    shutil.rmtree(p, ignore_errors=True)
        time.sleep(60)


class Handler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def setup(self):
        self.request.settimeout(15)
        super().setup()

    def log_message(self, *_):
        # Avoid logging pasted links and bearer download identifiers by default.
        pass

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        origin = self.headers.get('Origin', '').rstrip('/')
        if origin in ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        super().end_headers()

    def json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=True).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def check_origin(self):
        origin = self.headers.get('Origin', '').rstrip('/')
        host = self.headers.get('Host', '')
        # No forwarded-origin or client-IP trust. Reverse proxy must preserve Host.
        same = origin in {'https://' + host, 'http://' + host}
        if origin and not same and origin not in ORIGINS:
            raise APIError('This frontend origin is not allowed by the backend.', 403)

    def do_OPTIONS(self):
        try:
            self.check_origin()
            self.send_response(204)
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Content-Length', '0')
            self.end_headers()
        except APIError as e:
            self.json({'error': e.message, 'code': e.code}, e.status)

    def do_POST(self):
        try:
            self.connection.settimeout(90)
            self.check_origin()
            path = urlsplit(self.path).path
            if path not in ('/api/inspect', '/api/download'):
                raise APIError('Endpoint not found.', 404)
            if self.headers.get('Transfer-Encoding'):
                raise APIError('Chunked request bodies are not supported.', 400)
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                raise APIError('Use a JSON request body.', 415)
            length = int(self.headers.get('Content-Length', '0'))
            if not 1 <= length <= 8192:
                self.close_connection = True
                raise APIError('Request body is too large or missing.', 413)
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict) or data.get('permission') is not True:
                raise APIError('Confirm that you have permission to download the content.')
            ip = self.client_address[0]
            with lock:
                now = time.time()
                history = rate_log[ip]
                while history and now - history[0] > 60:
                    history.popleft()
                if len(history) >= int(os.environ.get('RDX_REQUESTS_PER_MINUTE', '8')):
                    raise APIError('Too many requests. Wait one minute and try again.', 429)
                if len(rate_log) > 10000:
                    raise APIError('The server is busy. Please try again later.', 503)
                history.append(now)
            result = inspect(data.get('url')) if path.endswith('inspect') else create_job(data)
            self.json(result, 200 if path.endswith('inspect') else 202)
        except APIError as e:
            self.close_connection = True
            self.json({'error': e.message, 'code': e.code}, e.status)
        except (ValueError, TypeError, OSError):
            self.close_connection = True
            self.json({'error': 'Invalid request, public URL, or request body.'}, 400)
        except Exception:
            self.json({'error': 'The request could not be completed.'}, 500)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        try:
            self.connection.settimeout(90)
            path = unquote(urlsplit(self.path).path)
            if path == '/api/platforms':
                return self.json({'platforms': PLATFORMS, 'scope': 'Public accessible content only; source and host restrictions still apply.'})
            if path == '/api/health':
                return self.json({'service': 'RdxDownloader', 'version': (ROOT / 'VERSION').read_text().strip(),
                                  'downloadsReady': settings_ready(), 'dependencies': dependency_status(), 'maxFileMB': MAX_BYTES // 1048576,
                                  'maxDurationSeconds': MAX_DURATION})
            if path.startswith('/api/jobs/'):
                token = path.removeprefix('/api/jobs/')
                with lock:
                    job = jobs.get(token)
                    if not job or time.time() - job['created'] > TTL:
                        raise APIError('This job expired or was not found.', 404)
                    result = {k: v for k, v in job.items() if k not in ('file', 'name', 'created')}
                    if job['status'] == 'ready':
                        result['downloadUrl'] = '/api/files/' + token
                return self.json(result)
            if path.startswith('/api/files/'):
                token = path.removeprefix('/api/files/')
                with lock:
                    job = jobs.get(token)
                    if not job or job['status'] != 'ready' or time.time() - job['created'] > TTL:
                        raise APIError('This file expired or is not ready.', 404)
                    file = Path(job['file'])
                    name = job['name']
                if not file.is_file():
                    raise APIError('The temporary file is no longer available.', 410)
                self.send_response(200)
                self.send_header('Content-Type', mimetypes.guess_type(name)[0] or 'application/octet-stream')
                self.send_header('Content-Length', str(file.stat().st_size))
                self.send_header('Content-Disposition', 'attachment; filename="' + name + '"')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                if self.command != 'HEAD':
                    with file.open('rb') as f:
                        shutil.copyfileobj(f, self.wfile, length=256 * 1024)
                return
            # Strict static allowlist: never serve backend code, .env, .git or job storage.
            if path in ('/', '/index.html', '/VERSION', '/ads.txt', '/robots.txt') or path.startswith('/assets/'):
                normalized = (ROOT / path.lstrip('/')).resolve()
                if path == '/':
                    normalized = ROOT / 'index.html'
                if not normalized.is_relative_to(ROOT) or any(part.startswith('.') for part in normalized.relative_to(ROOT).parts):
                    raise APIError('Not found.', 404)
                if path.startswith('/assets/') and (not normalized.is_relative_to(ROOT / 'assets') or not normalized.is_file() or normalized.suffix.lower() not in {'.js', '.css', '.svg', '.png', '.jpg', '.webp', '.ico'}):
                    raise APIError('Not found.', 404)
                return super().do_GET() if self.command != 'HEAD' else super().do_HEAD()
            raise APIError('Not found.', 404)
        except APIError as e:
            self.json({'error': e.message, 'code': e.code}, e.status)
        except (BrokenPipeError, ConnectionResetError, FileNotFoundError):
            self.close_connection = True

    def list_directory(self, _):
        self.json({'error': 'Not found.'}, 404)
        return None


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, *args, **kwargs):
        self.http_slots = threading.BoundedSemaphore(32)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self.http_slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.http_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.http_slots.release()


def main():
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(DATA, 0o700)
    threading.Thread(target=cleanup, daemon=True).start()
    server = Server((HOST, PORT), Handler)
    print(f'RdxDownloader {(ROOT / "VERSION").read_text().strip()} at http://{HOST}:{PORT}', flush=True)
    print('Use HTTPS reverse proxy + egress restrictions in production. One process/replica only.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        executor.shutdown(wait=False, cancel_futures=True)


if __name__ == '__main__':
    main()
