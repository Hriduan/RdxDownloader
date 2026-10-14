"""One yt-dlp task per process. Input/output are JSON via stdin/stdout.
Do not enable user-controlled options, cookies, external downloaders,
remote JS component downloads or FFmpeg network downloading. Bundled EJS runs through Deno’s sandbox.
"""
import json
import os
from pathlib import Path
import re
import sys
import time
if __package__:
    from .network import install_socket_guard, validate_url
    from .runtime import runtime_options
    from .platforms import normalize_url
    from .errors import describe_error
else:
    from network import install_socket_guard, validate_url
    from runtime import runtime_options
    from platforms import normalize_url
    from errors import describe_error

ROOT = Path(__file__).resolve().parents[1]
PROTOCOLS = {'http', 'https', 'm3u8_native', 'http_dash_segments'}
EXTENSIONS = {'mp4', 'webm', 'mkv', 'mov', 'm4a', 'mp3', 'ogg', 'opus', 'flac', 'wav', 'aac', 'flv', 'ts', '3gp'}
SAFE_ID = re.compile(r'^[A-Za-z0-9_.-]{1,128}$')


class QuietLogger:
    def debug(self, *_):
        pass
    def warning(self, *_):
        pass
    def error(self, *_):
        pass


def emit(value):
    print(json.dumps(value, ensure_ascii=True), flush=True)


def eligible(f):
    return (not f.get('has_drm') and f.get('protocol') in PROTOCOLS
            and f.get('ext') in EXTENSIONS and SAFE_ID.fullmatch(str(f.get('format_id', ''))))


def source_formats(info):
    """yt-dlp's direct-media result can be a single top-level format, not a list."""
    listed = info.get('formats')
    if isinstance(listed, list) and listed:
        return listed
    if not isinstance(info.get('url'), str) or not info['url']:
        return []
    single = dict(info)
    single['format_id'] = str(single.get('format_id') or '0')
    return [single] if eligible(single) else []


def format_catalog(info):
    raw = [f for f in source_formats(info) if eligible(f)]
    audio = [f for f in raw if f.get('vcodec') == 'none' and f.get('acodec') not in (None, 'none')]
    catalog = []
    for f in raw:
        unknown = f.get('vcodec') is None and f.get('acodec') is None
        audio_extensions={'m4a','mp3','ogg','opus','flac','wav','aac'}
        video = f.get('vcodec') not in (None, 'none') or unknown and f['ext'] not in audio_extensions
        has_audio = f.get('acodec') not in (None, 'none') or unknown and f['ext'] in audio_extensions
        if not video and not has_audio:
            continue
        separate = video and f.get('acodec')=='none'
        candidates = audio
        if separate and f['ext'] == 'mp4' and any(x['ext'] == 'm4a' for x in audio):
            candidates = [x for x in audio if x['ext'] == 'm4a']
        af = max(candidates, key=lambda x: x.get('abr') or x.get('tbr') or 0, default=None) if separate else None
        size = f.get('filesize') or f.get('filesize_approx')
        if size and af:
            extra = af.get('filesize') or af.get('filesize_approx')
            size = size + extra if extra else None
        height = f.get('height')
        fps = f.get('fps')
        codec = f.get('vcodec') if video else f.get('acodec')
        # Lossless merging: never promise a particular MP4 codec combination.
        mp4_safe = af and f['ext']=='mp4' and af['ext']=='m4a' and str(f.get('vcodec','')).startswith(('avc','h264')) and str(af.get('acodec','')).startswith(('mp4a','aac'))
        container = ('mp4' if mp4_safe else 'mkv') if af else f['ext']
        catalog.append({
            'id': str(len(catalog)), 'rawId': str(f['format_id']),
            'audioId': str(af['format_id']) if af else None,
            'kind': 'video' if video else 'audio',
            'label': (str(height) + 'p') if video and height else ('Source media' if unknown and video else 'Source video' if video else str(round(f.get('abr') or f.get('tbr'))) + ' kbps' if f.get('abr') or f.get('tbr') else 'Source audio'),
            'height': height or 0, 'fps': round(fps, 2) if fps else None,
            'codec': str(codec or 'source').split('.')[0], 'container': container,
            'size': int(size) if size else None,
            'audioLabel': 'Audio availability unknown' if unknown and video else 'Video + merged audio' if af else 'Video + audio' if video and has_audio else 'Silent source video' if video else 'Audio only',
        })
    catalog.sort(key=lambda f: (f['kind'] == 'video', f['height'], f['fps'] or 0, f['size'] or 0), reverse=True)
    return catalog


def main():
    payload = json.loads(sys.stdin.read(32768))
    install_socket_guard()
    url = validate_url(normalize_url(payload.get('url')))
    import yt_dlp
    from yt_dlp.downloader.external import FFmpegFD
    def deny_remote_ffmpeg(*args, **kwargs):
        raise ValueError('This stream requires a network downloader that is disabled for safety.')
    FFmpegFD.real_download = deny_remote_ffmpeg
    options = {
        'quiet': True, 'no_warnings': True, 'logger': QuietLogger(),
        'noplaylist': True, 'playlistend': 1, 'skip_download': True,
        'socket_timeout': 20, 'retries': 1, 'fragment_retries': 1,
        'cachedir': False, 'proxy': '', 'geo_bypass': False,
        'allowed_extractors': ['default'],
        'js_runtimes': runtime_options(), 'remote_components': [],
        'extractor_args': {'youtube-ejs': {'jitless': ['true']}},
        'check_formats': 'selected',
        'extractor_retries': 1, 'ignoreerrors': False,
    }
    if payload['operation'] == 'inspect':
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info or info.get('_type') in ('playlist', 'multi_video') or 'entries' in info:
            raise ValueError('Use a single public video link, not a playlist.')
        if info.get('is_live') or info.get('live_status') == 'is_live':
            raise ValueError('Live streams are not supported.')
        if info.get('duration') and info['duration'] > int(payload['maxDuration']):
            raise ValueError('This video exceeds the host duration limit.')
        formats = format_catalog(info)
        if not formats:
            raise ValueError('No supported unprotected formats were exposed by this source.')
        emit({'ok': True, 'title': str(info.get('title') or 'Untitled video')[:300],
              'platform': str(info.get('extractor_key') or 'Public source')[:80],
              'duration': info.get('duration'), 'uploader': str(info.get('uploader') or '')[:120], 'formats': formats})
        return
    if payload['operation'] != 'download':
        raise ValueError('Unknown worker operation.')
    selected = payload['selected']
    ids = [selected['rawId']] + ([selected['audioId']] if selected.get('audioId') else [])
    if any(not SAFE_ID.fullmatch(x) for x in ids):
        raise ValueError('Invalid source format.')
    target = Path(payload['directory']).resolve()
    target.mkdir(parents=True, exist_ok=True)
    last_update = [0.0]

    def progress(data):
        if time.monotonic() - last_update[0] < .4:
            return
        last_update[0] = time.monotonic()
        downloaded = data.get('downloaded_bytes', 0)
        if downloaded > int(payload['maxBytes']):
            raise ValueError('This file exceeds the host size limit.')
        total = data.get('total_bytes') or data.get('total_bytes_estimate')
        emit({'progress': min(92, round(downloaded / total * 90, 1)) if total else None,
              'detail': 'Downloading source streams. Separate streams may restart the progress estimate.'})

    options.update({
        'skip_download': False, 'format': '+'.join(ids),
        'outtmpl': str(target / 'media.%(ext)s'),
        'merge_output_format': selected.get('container') if selected.get('container') in ('mp4','mkv','webm') else 'mkv',
        'max_filesize': int(payload['maxBytes']),
        'ratelimit': int(payload['rateBytes']),
        'concurrent_fragment_downloads': 1,
        'hls_prefer_native': True, 'external_downloader': None,
        'progress_hooks': [progress],
        'match_filter': lambda i, **_: 'Duration limit exceeded' if i.get('duration') and i['duration'] > int(payload['maxDuration']) else None,
        'postprocessor_hooks': [lambda _: emit({'progress': 95, 'detail': 'Merging source streams without re-encoding.'})],
        'overwrites': False, 'writethumbnail': False, 'writeinfojson': False,
    })
    # Re-check the selected protocol/DRM state after a fresh extraction. Do not silently
    # fall back to a different resolution or invoke FFmpeg on remote URLs.
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info or info.get('is_live') or 'entries' in info:
            raise ValueError('This source is no longer an eligible single video.')
        current = {str(f.get('format_id')): f for f in source_formats(info) if eligible(f)}
        if any(x not in current for x in ids):
            raise ValueError('This format changed or is no longer supported. Inspect the link again.')
        ydl.process_info(info)
    files = [p for p in target.iterdir() if p.is_file() and p.suffix.lower().lstrip('.') in EXTENSIONS]
    if len(files) != 1:
        raise ValueError('The source streams could not be combined into one downloadable file.')
    file = files[0]
    if file.stat().st_size < 1 or file.stat().st_size > int(payload['maxBytes']):
        raise ValueError('The prepared file is empty or exceeds the host size limit.')
    emit({'ok': True, 'file': file.name, 'bytes': file.stat().st_size})


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # Do not return signed CDN URLs, filesystem paths, credentials or provider traces.
        emit({'ok': False, **describe_error(e)})
        sys.exit(1)
