"""Runtime checks shared by the server, worker and local doctor. No request-time installs."""
import importlib.util
import importlib.metadata
import os
from pathlib import Path
import shutil
import tempfile
import sys


def deno_executable():
    configured=os.environ.get('RDX_DENO_PATH')
    if configured:return configured
    found=shutil.which('deno')
    if found:return found
    adjacent=Path(sys.executable).parent/'deno'
    return str(adjacent) if adjacent.is_file() and os.access(adjacent,os.X_OK) else None


def runtime_options():
    # Only Deno's sandboxed builtin EJS provider is enabled. No automatic remote components.
    path=deno_executable()
    os.environ.setdefault('DENO_DIR',str(Path(tempfile.gettempdir())/'rdx-deno-cache'))
    os.environ.setdefault('DENO_NO_UPDATE_CHECK','1')
    return {'deno':{'path':path}} if path else {}


def dependency_status():
    def installed(name):
        try:return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:return None
    ffmpeg=bool(shutil.which('ffmpeg'));ffprobe=bool(shutil.which('ffprobe'))
    ytdlp=installed('yt-dlp');ejs=installed('yt-dlp-ejs');deno=bool(deno_executable())
    return {'ytDlp':ytdlp,'ejs':ejs,'ffmpeg':ffmpeg,'ffprobe':ffprobe,'deno':deno,
            'downloadsReady':bool(ffmpeg and ffprobe and ytdlp),
            'youtubeRuntimeReady':bool(ytdlp and ejs and deno),
            'notes':'Dependency presence only, not proof of runtime version, platform availability or source access. Use python scripts/doctor.py for version checks.'}
