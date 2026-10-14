> **v1.0.1:** The complete package fixes safe ZIP-import publishing, adds a portable Termux temporary directory, Deno + bundled EJS, backend URL settings and an offline doctor. For the screenshot error and native Android startup read [TERMUX.md](TERMUX.md). The Docker build now installs requirements-docker.txt (including Deno); regular requirements.txt includes matched EJS/native HLS dependencies.

# Deploy RdxDownloader

## Pick a hosting mode

| Mode | What it runs | What you must provide |
|---|---|---|
| **Recommended: Docker on an HTTPS host** | Frontend + backend, same origin | A container-capable host, FFmpeg (in Docker), CPU/RAM/storage/egress |
| GitHub Pages + separate backend | Pages runs the frontend only | A deployed HTTPS backend and exact CORS origin |
| Local development | Full app on your computer | Python 3.11+, FFmpeg, yt-dlp |

The code is free software; hosting/traffic is not guaranteed free. Do not use GitHub Actions as a public download worker. Third-party platforms may block data-center IPs, require login, change extractors or restrict downloads. Supported extractors are not universal download guarantees.

## 1. Upload the repository

Extract the ZIP and upload **the contents of `RdxDownloader/`** to the root of https://github.com/Hriduan/RdxDownloader. `index.html`, `README.md`, `VERSION`, `Dockerfile` and `update` belong in the repo root. Include `.github/`, `.gitignore`, `.dockerignore` and `.nojekyll`. Review files before committing; do not overwrite unrelated work or upload private `.env` files.

## 2. Recommended: run the container

```bash
git clone https://github.com/Hriduan/RdxDownloader.git
cd RdxDownloader
cp .env.example .env
docker compose up --build -d
# Local-only test endpoint:
curl http://127.0.0.1:8080/api/health
```

Compose requires a recent Docker Compose supporting optional `env_file` entries. If yours does not, keep the copied `.env` and replace `env_file` with `env_file: .env`, or run plain Docker:

```bash
docker build -t rdxdownloader .
docker run --rm --init -p 127.0.0.1:8080:8080 --env-file .env \
  --read-only --tmpfs /tmp:size=4g,mode=1777 --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 128 --memory 2g \
  --cpus 2 rdxdownloader
```

On a managed container host, expose container port `8080`, retain a writable temporary directory and at least enough disk for concurrent input/output streams, and let the host terminate HTTPS. The Docker image runs as a non-root user. Keep **one replica/process**: inspections and job capabilities are in memory. A restart invalidates links; persistent/distributed queues are not implemented in v1.0.1.

Example Caddy reverse proxy (replace the example domain):

```caddyfile
download.example.com {
    request_body { max_size 16KB }
    reverse_proxy 127.0.0.1:8080
}
```

Caddy needs correct DNS and public ports 80/443. Configure request/IP limits, bandwidth controls, connection limits and bot/abuse controls at your reverse proxy or edge. Never blindly trust client-provided `X-Forwarded-For`. In-app rate limiting uses the connecting peer; behind a proxy this is shared. Set `RDX_REQUESTS_PER_MINUTE` to an appropriate shared ceiling **only after** adding per-client edge limits. Request inspection timeouts need at least 70 seconds; file downloads need appropriate streaming timeouts. Do not cache `/api/*`.

**Production network requirements:** block access to private networks, loopback, link-local/cloud metadata, internal DNS services and non-HTTP(S) egress at the container/host firewall. The Python worker additionally validates DNS and public destination IPs on each socket connection (including redirects/CDNs), pins the checked numeric address for that connection, disables proxy environment inheritance, and forbids FFmpeg remote downloading. DNS resolution itself uses the host resolver; do not expose internal DNS to untrusted workers. Application guards are defense in depth, not a security audit or substitute for network isolation.

## 3. Optional: GitHub Pages frontend

1. Deploy the backend on an HTTPS root origin first, e.g. `https://api.example.com`.
2. On the backend set `RDX_ALLOWED_ORIGINS=https://hriduan.github.io` (or your exact custom frontend origin, no URL path). Keep one backend replica.
3. Set GitHub repository variable **`RDX_API_BASE_URL`** to the backend HTTPS root origin.
4. In GitHub **Settings → Pages**, choose **GitHub Actions**.
5. Run the manually triggered **Deploy frontend only (backend required separately)** workflow.
6. Open `https://hriduan.github.io/RdxDownloader/` and check that the connection indicator is ready.

For a branch-based Pages deployment instead, set `apiBase` in `assets/js/config.js` to the backend HTTPS root origin, then publish the root folder. No private backend secrets go in this public file. The provided Pages workflow publishes a strict static allowlist, not the server directory.

GitHub Pages by itself will display the interface, but cannot inspect or download videos. The UI states “Backend setup required” rather than fabricating results.

## 4. Local development without Docker

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Install FFmpeg through your operating system package manager.
python -m server.app
```

Open `http://127.0.0.1:8080`. The HTTP server is standard library. Extraction uses yt-dlp’s default dependency group, including its matching EJS package; Docker separately installs Deno. On non-Docker Linux install a supported Deno and run `python scripts/doctor.py --strict`. FFmpeg performs local merging only. Shell helper `update` works in Bash (Linux/macOS/WSL/Git Bash); Windows users can instead run `python scripts/release.py`.

## 5. Limits and maintenance

| Variable | Default | Purpose |
|---|---|---|
| `RDX_MAX_FILE_MB` | 512 | Maximum completed file bytes; early source estimate check |
| `RDX_MAX_DURATION_SECONDS` | 1800 | Reject known-duration videos longer than 30 minutes |
| `RDX_MAX_JOB_SECONDS` | 1200 | Kill a download worker after 20 minutes |
| `RDX_MAX_WORKERS` | 2 | Combined inspection/download worker cap (1–4) |
| `RDX_RATE_BYTES` | 4194304 | Approximate per-job download speed limit (4 MiB/s) |
| `RDX_REQUESTS_PER_MINUTE` | 8 | Mutation requests per connecting peer |
| `RDX_DATA_DIR` | OS temp directory + `/rdxdownloader` | Private temporary media directory, outside public assets |
| `RDX_ALLOWED_ORIGINS` | empty | Comma-separated additional exact frontend origins |

There are at most twice as many active/queued download jobs as worker slots, at most 100 retained job records and 200 inspection records. Prepared jobs expire one hour after creation; expired files are deleted by cleanup normally within another minute. Metadata lasts 20 minutes. Active workers have runtime and disk ceilings. Unknown source sizes may hit limits only while downloading. Progress is an estimate and can restart when streams switch.

Review/update the pinned yt-dlp dependency regularly, re-test, rebuild and deploy. Deno is enabled for the locally installed matched EJS solver. Request-time remote components, insecure Node/Bun fallback, cookie/login imports, playlists and live streams remain disabled. Generic/public direct-media extraction is now best-effort, guarded by the same public-network checks and protocol restrictions. Platform restrictions can still prevent downloads. Do not solve blocked sources by disabling security checks or collecting visitor credentials.

## 6. Before public launch

- Replace the generic privacy/copyright contact wording with a monitored operator contact.
- Confirm your rights/abuse handling, local legal requirements, hosting terms and platform terms.
- Configure real domain-approved ad IDs and a genuine published CMP; see [ADVERTISING.md](ADVERTISING.md).
- Keep Google Auto ads, anchors and vignettes disabled if you require strict no-overlap behavior. Manual slots are outside the downloader; provider creatives themselves still require review.
- Add operator monitoring and disk/traffic alerts; this is a bounded starter, not a production security guarantee.
- Test an authorized, small public video that you own; verify actual audio, duration and dimensions. Never click your own ads or fabricate traffic.
