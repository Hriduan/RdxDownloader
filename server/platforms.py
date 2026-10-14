"""Host classification and conservative share-link cleanup; no access-control bypass."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
if __package__:
    from .network import validate_url
else:
    from network import validate_url

PLATFORMS = [
    {'id':'youtube','name':'YouTube','hosts':['youtube.com','youtu.be','youtube-nocookie.com'], 'note':'Public video/Shorts links; fuller extraction needs Deno + the matching EJS package. Some sources remain restricted.'},
    {'id':'facebook','name':'Facebook','hosts':['facebook.com','fb.watch','fb.com'], 'note':'Public watch/reel/share links when exposed without login; private and login-only videos are not supported.'},
    {'id':'instagram','name':'Instagram','hosts':['instagram.com','instagr.am'], 'note':'Public posts and reels when accessible without login; private content is not supported.'},
    {'id':'bilibili','name':'Bilibili','hosts':['bilibili.com','b23.tv','bilibili.tv'], 'note':'Public videos and short links; higher qualities may be account-, premium- or region-restricted.'},
    {'id':'tiktok','name':'TikTok','hosts':['tiktok.com'], 'note':'Public video/share links when the source exposes media; no added watermark, but embedded source marks may remain.'},
    {'id':'other','name':'Other / direct media','hosts':[], 'note':'Other yt-dlp extractors plus eligible direct public media. Generic pages are best-effort, not universal support.'},
]


def platform_for(url):
    host=(urlsplit(url).hostname or '').lower().rstrip('.')
    for item in PLATFORMS[:-1]:
        if any(host==h or host.endswith('.'+h) for h in item['hosts']):
            return item
    return PLATFORMS[-1]


def normalize_url(url):
    validate_url(url, resolve=False)
    parts=urlsplit(url)
    platform=platform_for(url)
    # Never strip arbitrary signatures or query fields from direct/CDN links.
    if platform['id']!='other':
        query=[(k,v) for k,v in parse_qsl(parts.query, keep_blank_values=True)
               if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid','igsh','igshid','si'}]
        return urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(query),parts.fragment))
    return url
