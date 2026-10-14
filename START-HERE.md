# RdxDownloader v1.0.2 — connected hosting

- Frontend: https://hriduan.github.io/RdxDownloader/
- Hosted engine and same-origin site: https://rdxdownloader.onrender.com
- Live health: https://rdxdownloader.onrender.com/api/health

The GitHub Pages configuration now selects the real backend automatically. Same-origin Docker/Termux hosting still uses its own engine. A blank old browser override no longer blocks the deployed default.

## Publish from your device

Extract this complete archive, copy its contents into your existing repository root (not an extra nested folder), and preserve `.git` and private settings. Review the changes. Then run:

```bash
bash update
```

No RELEASE confirmation word is needed. This is a publishing command; review before running it. `bash update --review` restores an interactive confirmation and `bash update --dry-run` changes nothing. Render auto-deploys main; GitHub Pages remains configured for main/root.

If Git identity or GitHub authentication has never been configured on YOUR device, run once:

```bash
bash scripts/setup-github.sh
```

Authorize with GitHub's device-code page in your own browser. The remote agent's browser login cannot configure your phone's Git credentials. The helper reuses GitHub CLI's normal credential storage. Without an OS keyring, gh may use a token file: protect your home directory, never share it, and use SSH/OS-agent authentication instead if you require encrypted credential storage. Tokens can expire or be revoked; no promise of permanent authentication is made.

## Free hosting limits

The selected Render plan is Free. It sleeps after 15 idle minutes and can take about a minute to wake. 128 MB/file, 10-minute source duration and one worker are configured to reduce resource usage. A host restart/deploy removes temporary files and job state. Monthly usage or external traffic limits may suspend service. No artificial keep-alive service is installed.

Use only public supported media you have permission to download. No watermark is added, but source watermarks may remain. No universal compatibility, DRM bypass or private-account access is provided. Ads remain disabled pending approved codes and consent setup.
