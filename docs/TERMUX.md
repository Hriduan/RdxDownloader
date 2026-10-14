# RdxDownloader v1.0.2 — Termux and the screenshot error

## What failed in the screenshot?

`Remote main is not an ancestor of HEAD` is a Git history mismatch, not a video-extraction error. A ZIP has no Git history. Initializing Git in that folder creates a history unrelated to the existing GitHub repository. The old helper refused to push it.

The complete v1.0.2 ZIP includes the fixed publisher. For a ZIP import/unrelated history it clones current remote `main` into temporary storage, overlays your reviewed local project files, commits on top of that remote history, and makes a normal atomic push with a new version tag. Remote-only files and GitHub history stay intact. Same-named remote files can be replaced by the local version; review the file list. Local deletions are not propagated in snapshot mode.

**Never delete .git, use reset --hard, or force push just to solve this error.**

## A. Replace the old package safely

1. Back up your existing project folder and any local customizations. Keep `.git`, private `.env` files and your GitHub credentials out of uploaded ZIPs.
2. Extract the complete updated ZIP. It contains one `RdxDownloader/` folder, with `index.html` immediately inside it.
3. Merge the **contents** into the intended project root. Do not accidentally create another nested RdxDownloader directory.
4. From the folder containing `index.html`, `VERSION`, `update` and `scripts/`, run:

```bash
bash update --dry-run
bash update
```

Review changes before running `bash update`: it now approves publishing without typing RELEASE. Use `bash update --review` if you want the old confirmation prompt. If you explicitly want fresh-remote snapshot mode even in a related checkout:

```bash
bash update --snapshot
```

The package version starts at **1.0.2**, but the actual helper fetches remote tags and advances beyond the highest published semantic version when necessary. A dry run is local-only; it does not inspect GitHub. No force push or account password collection is used. GitHub CLI may store its token in a file on devices without an OS keyring; see START-HERE.md.

Set your own Git author identity if Git asks for it:

```bash
git config user.name "Your Git author name"
git config user.email "Your Git author email"
```

Use secure GitHub authentication/SSH through your own Git setup. Do not store a token in source files, command examples, the ZIP or chat. Authentication failures, protected branches and concurrent remote changes are not bypassed by the helper.

## B. Run the downloader on the phone (separate from source upload)

Uploading/pushing the repository does not start a Python server. GitHub Pages only serves static frontend files. To run downloads locally on this phone, keep a native backend running in Termux.

On a supported **64-bit** native Termux installation:

```bash
cd /path/to/the/project/root
bash scripts/setup-termux.sh
bash start
```

The explicit installer uses official Termux packages (`python`, `python-yt-dlp`, `ffmpeg`, `git`, `deno`) and a private virtual environment under `$HOME/.local/share/rdxdownloader/venv`. That avoids putting executable virtualenv symlinks on Android shared storage. It does not download a Linux Deno wheel onto Android or run a remote curl-to-shell installer.

Then open:

```text
http://127.0.0.1:8080
```

Open it on the **same phone**, keep Termux running, and prevent the OS from suspending it while preparing files. This is a local test setup, not a dependable public backend. The service defaults to loopback, not all network interfaces. Do not expose a phone backend to the internet without the production protections in DEPLOYMENT.md.

The backend now uses the operating system's temporary directory, including Termux's `TMPDIR`, instead of assuming `/tmp` exists. A local `start` command detects either a project `.venv` or the Termux HOME virtualenv.

If package availability is stale, update the Termux package indexes/mirror through Termux's documented package management. Deno's current Termux package excludes 32-bit `arm` and `i686`; use a suitable 64-bit Docker/Linux backend for those clients. Native Android setup is documented but was **not run on a physical Android device** during this release's tests.

## C. Diagnose missing tools

```bash
# If setup-termux.sh created the HOME environment:
"$HOME/.local/share/rdxdownloader/venv/bin/python" scripts/doctor.py --strict

# Activated/project Python environment:
python scripts/doctor.py --strict
```

The offline doctor checks FFmpeg, ffprobe, yt-dlp, a matching EJS solver, Deno version and writable temporary storage. It does not log in to platforms or download any media. Core tools may be ready while YouTube's runtime is missing; the interface now distinguishes these states.

The browser has **Backend settings** in the footer and **Set backend URL** when disconnected. Empty means this same-origin backend. For a separately hosted server enter its HTTPS root origin and allow the frontend's exact origin in `RDX_ALLOWED_ORIGINS`. Do not enter a GitHub repository URL as a backend.

## D. Platform scope

Facebook public watch/reels/share links, YouTube videos/Shorts, Instagram public posts/reels, Bilibili public BV/short links and TikTok public/share links are recognized and passed to their yt-dlp extractors. This is routing support, **not a guarantee of successful downloads**. Sources can require login, membership, premium quality, region access or refuse the backend IP. DRM/private access is not bypassed. The app adds no watermark; embedded source watermarks may remain.

## Official references

- https://github.com/yt-dlp/yt-dlp/wiki/EJS — supported runtimes and matching bundled solver
- https://github.com/termux/termux-packages/tree/master/packages/python-yt-dlp — native package
- https://github.com/termux/termux-packages/tree/master/packages/deno — Deno package and excluded architectures

## Hosted backend

The deployed Render engine is https://rdxdownloader.onrender.com. You do not need to keep Termux running for the hosted service. Local Termux startup remains an alternative. The hosted Free plan sleeps and has usage limits. `bash scripts/setup-github.sh` is one-time GitHub device authorization on your phone; later `bash update` reuses it until it expires or is revoked.
