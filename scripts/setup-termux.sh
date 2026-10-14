#!/usr/bin/env bash
# Explicitly invoked installer; installs trusted Termux packages, never curl|sh scripts.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if ! command -v pkg >/dev/null 2>&1; then echo 'This installer is for native Termux only. See docs/DEPLOYMENT.md for Docker/Linux.'; exit 1; fi
case "$(uname -m)" in
  aarch64|x86_64) ;;
  *) echo 'This Deno-based setup requires a supported 64-bit Termux architecture. Use the Docker backend on a suitable host for this device.'; exit 1 ;;
esac
printf 'Installing Python, Git, native FFmpeg, yt-dlp and Deno through Termux pkg.\n'
pkg update
pkg install python python-yt-dlp ffmpeg git deno
# Android shared storage may not support executable symlinks. Install runtime in HOME.
ENV_DIR="$HOME/.local/share/rdxdownloader/venv"
mkdir -p "$(dirname "$ENV_DIR")"
python -m venv --system-site-packages "$ENV_DIR"
"$ENV_DIR/bin/python" -m pip install -r requirements-termux.txt
"$ENV_DIR/bin/python" scripts/doctor.py --strict
printf '\nSetup complete. To run from this project folder:\n'
printf '  %q -m server.app\n' "$ENV_DIR/bin/python"
printf 'Or use: bash start (it detects this Termux runtime).\n'
printf 'Open http://127.0.0.1:8080 on the same phone. Keep Termux running.\n'
