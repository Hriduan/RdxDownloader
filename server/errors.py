"""Safe actionable errors without provider traces, signed CDN URLs or filesystem paths."""

def describe_error(error):
    message=str(error).lower()
    groups=[
        (('private, reserved','private destination','internal network','standard ports','public http'), 'public_url_only', 'Only public HTTP/HTTPS media is allowed. Local, private-network and nonstandard-port destinations remain blocked.'),
        (('drm','encrypted with drm'), 'protected_source', 'This source is DRM-protected. RdxDownloader does not bypass DRM or other access controls.'),
        (('sign in','log in','login required','login_required','private video','cookies are needed','cookies required','only available for registered','members-only'), 'source_login_required', 'This source requires an account, membership or private access. Use an authorized publicly accessible video; this server does not accept login cookies.'),
        (('javascript runtime','challenge solver','n challenge','signature extraction','nsig','ejs'), 'runtime_setup', 'YouTube extraction needs the matching yt-dlp-ejs package and a supported Deno runtime. Run python scripts/doctor.py on the backend host.'),
        (('429','too many requests','rate limit'), 'source_rate_limited', 'The source is rate-limiting the backend. Wait before retrying. Repeated automatic requests are not made.'),
        (('403','forbidden','not a bot','automated requests'), 'source_blocked', 'The source refused this backend request. Its access rules or anti-automation checks may prevent downloading even when the link works in a browser.'),
        (('not available in your country','geo restricted','geo-restricted','geographic'), 'source_region_restricted', 'The source is not available in the backend’s region. This app does not unlock region-restricted content.'),
        (('unsupported url','unsupportedurl'), 'unsupported_url', 'No supported extractor or direct public media was found at this URL. Use the video’s own public share/watch link, not a profile or search page.'),
        (('requested format','no video formats','no supported unprotected','format changed'), 'format_unavailable', 'The source did not expose an eligible format, or its formats changed. Inspect the link again; restricted qualities cannot be unlocked here.'),
        (('timed out','timeout','name resolution','certificate verify'), 'source_connection_failed', 'The backend could not establish a verified connection to the source. Check host DNS/network access and retry later.'),
    ]
    for needles,code,text in groups:
        if any(n in message for n in needles):return {'error':text,'code':code}
    # ValueErrors raised by this module's own workflow use these known fixed messages.
    safe_prefixes=('use a single public','live streams are not','this video exceeds','invalid source format',
                   'this stream requires','this file exceeds','the source streams could not','the prepared file is empty',
                   'this source is no longer','unknown worker operation')
    if isinstance(error,ValueError) and message.startswith(safe_prefixes):
        return {'error':str(error)[:350],'code':'source_or_host_limit'}
    return {'error':'The source could not be processed. It may be unsupported, removed, restricted, or unavailable to this backend. Check the public link and backend diagnostics.','code':'source_unavailable'}
