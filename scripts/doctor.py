#!/usr/bin/env python3
"""Offline host diagnostics. Does not download media, install packages or contact GitHub."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server.runtime import dependency_status, runtime_options


def diagnose():
    status=dependency_status();checks=[]
    for command in ('ffmpeg','ffprobe','deno'):
        executable=(runtime_options().get('deno') or {}).get('path') if command=='deno' else shutil.which(command)
        if not executable:
            checks.append({'name':command,'ok':False,'detail':'Not found on PATH'});continue
        try:
            result=subprocess.run([executable,'--version' if command=='deno' else '-version'],capture_output=True,text=True,timeout=8)
            first=(result.stdout or result.stderr).splitlines()[0]
            valid=result.returncode==0
            if command=='deno':
                match=re.search(r'deno (\d+)\.(\d+)\.(\d+)',first)
                valid=valid and bool(match) and tuple(map(int,match.groups()))>=(2,3,0)
            checks.append({'name':command,'ok':valid,'detail':first[:160]})
        except (OSError,subprocess.TimeoutExpired,IndexError):checks.append({'name':command,'ok':False,'detail':'Could not execute/version-check this binary'})
    expected=None
    if status['ytDlp']:
        for req in importlib.metadata.requires('yt-dlp') or []:
            m=re.match(r'yt-dlp-ejs==([\d.]+)',req)
            if m:expected=m.group(1);break
    checks.extend([{'name':'yt-dlp','ok':bool(status['ytDlp']),'detail':status['ytDlp'] or 'Not installed'},
                   {'name':'EJS matched','ok':bool(status['ejs'] and (not expected or status['ejs']==expected)),
                    'detail':f"Installed {status['ejs'] or 'none'}; expected {expected or 'version supported by the installed extractor'}"}])
    try:
        with tempfile.TemporaryDirectory(prefix='rdx-doctor-') as d:(Path(d)/'probe').write_text('ok')
        temp_ok=True
    except OSError:temp_ok=False
    checks.append({'name':'Temporary storage','ok':temp_ok,'detail':'Writable' if temp_ok else 'Not writable; set TMPDIR/RDX_DATA_DIR'})
    core=all(c['ok'] for c in checks if c['name'] in ('ffmpeg','ffprobe','yt-dlp','Temporary storage'))
    return {'version':(ROOT/'VERSION').read_text().strip(),'checks':checks,'coreReady':core,
            'youtubeRuntimeReady':core and all(c['ok'] for c in checks if c['name'] in ('deno','EJS matched')),
            'scope':'Offline dependency/runtime checks only. This does not establish that any platform or URL is accessible.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--json',action='store_true');p.add_argument('--strict',action='store_true');a=p.parse_args();report=diagnose()
    if a.json:print(json.dumps(report,indent=2))
    else:
        print(f"RdxDownloader v{report['version']} — backend doctor (offline)")
        for c in report['checks']:print(f"{'OK  ' if c['ok'] else 'FIX '} {c['name']}: {c['detail']}")
        print('Core downloads: '+('ready' if report['coreReady'] else 'setup needed'))
        print('YouTube runtime: '+('ready' if report['youtubeRuntimeReady'] else 'install matching EJS + Deno; see docs/TERMUX.md'))
        print(report['scope'])
    return 0 if report['coreReady'] and (not a.strict or report['youtubeRuntimeReady']) else 1

if __name__=='__main__':sys.exit(main())
