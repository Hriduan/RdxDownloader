#!/usr/bin/env python3
"""Dependency-free source structure and ad separation checks."""
from html.parser import HTMLParser
from pathlib import Path
import ast
import re

ROOT = Path(__file__).resolve().parents[1]


class Audit(HTMLParser):
    def __init__(self):
        super().__init__(); self.stack = []; self.slots = []; self.ids = set(); self.duplicates = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        identity = attrs.get('id')
        if identity:
            if identity in self.ids: self.duplicates.append(identity)
            self.ids.add(identity)
        if 'data-ad-placement' in attrs:
            assert not any(a.get('id') == 'downloader' for _, a in self.stack), 'Ad overlaps downloader DOM'
            self.slots.append(attrs['data-ad-placement'])
        if tag not in {'input', 'img', 'link', 'meta', 'br', 'hr', 'source'}:
            self.stack.append((tag, attrs))
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]; break


def main():
    for item in ['index.html','README.md','update','VERSION','server/app.py','server/worker.py','Dockerfile','assets/js/config.js','docs/DEPLOYMENT.md']:
        assert (ROOT/item).is_file(), item
    version = (ROOT/'VERSION').read_text().strip()
    assert re.fullmatch(r'\d+\.\d+\.\d+', version)
    parser = Audit(); parser.feed((ROOT/'index.html').read_text())
    assert not parser.duplicates, parser.duplicates
    assert len(parser.slots) == len(set(parser.slots)) == 12
    for p in (ROOT/'server').glob('*.py'): ast.parse(p.read_text())
    for p in (ROOT/'scripts').glob('*.py'): ast.parse(p.read_text())
    for p in ROOT.rglob('*'):
        if p.is_file() and '.git' not in p.parts:
            assert p.name != '.env', 'Private .env must not ship'
    script = (ROOT/'scripts/release.py').read_text()
    assert "'--force'" not in script and 'credential.helper store' not in script
    print(f'PASS: v{version}, root entry point, 12 unique ad slots outside downloader, source syntax and release safeguards.')


if __name__ == '__main__': main()
