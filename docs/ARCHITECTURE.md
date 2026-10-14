# Architecture and limitations

```text
Browser (index.html + assets/)
   │  POST /api/inspect  {url, permission:true}
   ▼
Bounded HTTP server ── local-memory inspection capability (20 min)
   │  disposable Python worker / yt-dlp
   │  public-only IP guard / supported extractors / no credentials
   ▼
Format list (source dimensions + audio availability; not guessed)
   │  POST /api/download {inspection, format, permission:true}
   ▼
Bounded worker queue ── native stream fetch ── local FFmpeg merge
   │  poll GET /api/jobs/{random-capability}
   ▼
GET /api/files/{random-capability} → temporary attachment (1 hour)
```

- No third-party “free downloader API” or hidden paid API dependency.
- Extraction is source/platform dependent and may fail for many valid URLs.
- HTTP(S), native HLS and native DASH formats only; best-effort generic/direct-media extractor; FFmpeg remote downloading stays disabled.
- No live streams, playlists, login/session-cookie uploads, DRM bypass, source watermark removal or upscaling.
- Audio-only uses the original available audio container; it is not falsely labeled MP3 when the source provides M4A/WebM/Opus.
- Lossless local merging uses MP4 for compatible H.264/AAC MP4/M4A pairs, otherwise MKV for separate streams. Progressive MP4 keeps MP4. The source sets codec and quality; not every player handles every source codec.
- Automatic format fallback to a different resolution is not performed. Inspect again if a chosen format expires.
- Metadata and job records are in memory; bearer capability URLs are not accounts or access-controlled libraries. Restarts invalidate links. Do not log/share tokens.
- A completed file is streamed through the backend, not exposed as an arbitrary public file path. Internal worker options and CDN URLs are not returned to clients.
- v1.0.1 is a **single-host/single-process** application. Multi-replica deployment needs a shared durable queue/store, authenticated job ownership, centralized limits and security review.

## Public API

| Endpoint | Method | Result |
|---|---|---|
| `/api/health` | GET | Version, dependency readiness, host limits |
| `/api/inspect` | POST | Inspection capability, title, public source format catalog |
| `/api/download` | POST | Job capability, HTTP 202 |
| `/api/jobs/{id}` | GET | Queued/processing/ready/error and estimated progress |
| `/api/files/{id}` | GET/HEAD | Temporary completed media attachment |

Mutation bodies must be JSON and include `permission:true`. Inspection and format identifiers are returned by the service, not raw yt-dlp option strings. CORS is exact-origin allowlisted; no credentialed browser sessions are used.

## Security scope

Initial URLs reject non-HTTP(S), credentials, custom ports and nonpublic targets. Disposable extraction workers check public destination addresses again for all Python socket connections, including redirects and CDN requests. Native networking is pinned to the checked IP per connection; remote FFmpeg download fallback and inherited proxies are disabled. Local FFmpeg merging uses only server-generated file paths. Resource ceilings, a bounded queue, private temp storage and route allowlisting reduce exposure.

These safeguards are not a penetration test. Add a host/container egress firewall, DNS isolation, HTTPS, reverse-proxy request/connection/IP limits, abuse handling, updated dependencies and monitoring before inviting public traffic. TLS validation remains enabled. Never disable the public-only checks to “support” internal links.

## v1.0.1 runtime

Deno executes the installed matched EJS solver with the upstream sandbox/no-remote flags. No automatic Node/Bun fallback is enabled. Generic/direct public-media extraction uses the same Python socket checks; FFmpeg remote downloading is still blocked. Termux temp paths use Python tempfile.gettempdir(), not an assumed Linux /tmp. Diagnostics report local dependencies, not real platform accessibility.
