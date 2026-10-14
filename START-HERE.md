# RdxDownloader v1.0.1 — start here

1. This ZIP contains **all** files. Extract the single RdxDownloader folder and upload/merge its contents into the repository root, including hidden .github files. Preserve .git, private configuration and your newer work.
2. **The screenshot's Git history error is fixed in the included update helper.** Run `bash update --dry-run`, then `bash update` and review the snapshot before typing RELEASE. No force push or history reset is used. See docs/TERMUX.md.
3. Source upload is not backend deployment. GitHub Pages cannot run Python/FFmpeg. On supported 64-bit Termux: `bash scripts/setup-termux.sh`, then `bash start`. Open http://127.0.0.1:8080 on the same phone while Termux runs.
4. For public hosting, use the included Docker backend and docs/DEPLOYMENT.md. The browser now has Backend settings to connect a separately deployed HTTPS origin.
5. Run `python scripts/doctor.py --strict` using the backend's Python environment. Full YouTube extraction needs a matching EJS solver + Deno, now included in the Linux Docker requirements and native Termux setup.
6. Facebook, YouTube, Instagram, Bilibili and TikTok link families are recognized; other extractors/direct public media are best-effort. No private access, DRM bypass, source watermark removal, universal compatibility, unlimited resolution or missing-audio restoration is promised.
7. Twelve manual ad positions remain outside the downloader. They are disabled until you supply approved codes for this domain. See docs/ADVERTISING.md.

Before public launch add a monitored operator contact, HTTPS, egress isolation, edge abuse limits and required privacy/rights notices. The code is free; hosting/bandwidth and provider approvals are not guaranteed free.
