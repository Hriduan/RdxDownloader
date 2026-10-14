#!/usr/bin/env python3
"""Safe RdxDownloader releases, including ZIP imports into an existing repository.
No force pushes, destructive resets, credential storage, or automatic conflict resolution.
"""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/Hriduan/RdxDownloader.git'


def git(*args, check=True, capture=True, cwd=None):
    result = subprocess.run(['git', *args], cwd=cwd or ROOT, text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None)
    if check and result.returncode:
        if capture and result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, ['git', *args])
    return result


def next_version(current, tags):
    if not re.fullmatch(r'\d+\.\d+\.\d+', current):
        raise ValueError('VERSION must contain major.minor.patch.')
    parsed=[tuple(map(int,t[1:].split('.'))) for t in tags if re.fullmatch(r'v\d+\.\d+\.\d+',t)]
    current_tuple=tuple(map(int,current.split('.')))
    highest=max(parsed,default=None)
    if highest is None or current_tuple>highest:
        return current
    major,minor,patch=highest
    return f'{major}.{minor}.{patch+1}'



def exists(ref, cwd=None):
    return git('rev-parse', '--verify', ref, cwd=cwd, check=False).returncode == 0


def forbidden(path):
    p = Path(path)
    return (p.is_absolute() or '..' in p.parts or '.git' in p.parts
            or any(part in ('downloads', 'data', '.venv', 'venv', 'node_modules', '__pycache__') for part in p.parts)
            or p.name.startswith('.env') and p.name != '.env.example'
            or p.suffix.lower() in ('.pem', '.key', '.pyc'))


def project_files():
    # Respect the user's .gitignore, including ignored private files. Also include
    # already tracked files, then reject unsafe/private paths before any staging.
    result = git('ls-files', '-z', '--cached', '--others', '--exclude-standard').stdout
    files = []
    for rel in sorted(set(result.split('\0')) - {''}):
        source = ROOT / rel
        if forbidden(rel):
            raise ValueError('Private/runtime path must be removed from the tracked/publishable set: ' + rel)
        if source.is_symlink():
            raise ValueError('Symlinks are not copied by the snapshot publisher: ' + rel)
        if source.is_file():
            if not source.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError('Source path escapes the project directory: ' + rel)
            files.append(rel)
    if 'VERSION' not in files or 'index.html' not in files:
        raise ValueError('Run this helper from the complete RdxDownloader project with index.html and VERSION.')
    return files


def check_identity():
    # Local author settings are used only for authoring, never credentials. A clone
    # does not inherit repository-local user.name/user.email, so pass them per command.
    values = []
    for name in ('user.name', 'user.email'):
        result = git('config', '--get', name, check=False)
        if result.returncode or not result.stdout.strip():
            raise ValueError('Git identity is missing. Run bash scripts/setup-github.sh once, or set git config user.name and user.email in this project.')
        values.extend(['-c', name + '=' + result.stdout.strip()])
    return values


def remote_origin():
    result = git('remote', 'get-url', 'origin', check=False)
    if result.returncode:
        git('remote', 'add', 'origin', REPO)
        return REPO
    origin = result.stdout.strip()
    permitted = {REPO, REPO.removesuffix('.git')}
    if REPO.startswith('https://github.com/'):
        permitted.add('git@github.com:Hriduan/RdxDownloader.git')
    if origin not in permitted:
        raise ValueError('origin points to another repository. Refusing to change it or push.')
    return origin


def confirm(planned, files, snapshot, yes):
    print(f'\nRepository: {REPO}\nRelease: v{planned}', flush=True)
    git('status', '--short', capture=False)
    if snapshot:
        print('\nZIP/import or divergent-history mode: publish from a fresh temporary clone of remote main.')
        print('GitHub history and remote-only files are retained. Your local .git and commits are left intact.')
        print('Local publishable files replace same-named remote files; review that this folder is the version you want.')
        print('Local deletions are NOT propagated in this mode. Newer remote edits to copied paths may be replaced.')
        print(f'Files in the local publishable snapshot ({len(files)}):')
        for rel in files:
            print('  ' + rel)
    else:
        print('Stage reviewed project changes, commit if needed, and create a new annotated release tag.')
    print('The helper pushes main and its new tag atomically. No force push or credential storage is used.')
    if not yes and input('Type RELEASE to continue: ').strip() != 'RELEASE':
        print('Cancelled. No project files were staged, committed or pushed.')
        return False
    return True


def publish_snapshot(origin, files, planned, identity):
    # Original checkout/history/index are never reset, merged, checked out or cleaned.
    # A failed push leaves them intact. Fresh clone makes the release a child of
    # remote main even when the imported ZIP has unrelated or no local commits.
    with tempfile.TemporaryDirectory(prefix='rdx-release-') as temporary:
        checkout = Path(temporary) / 'repo'
        git('clone', '--single-branch', '--branch', 'main', '--', origin, str(checkout), capture=False)
        if exists('refs/tags/v' + planned, cwd=checkout):
            raise ValueError('This release tag appeared remotely. Fetch and review before retrying.')
        for rel in files:
            target = checkout / rel
            if not target.parent.resolve().is_relative_to(checkout.resolve()):
                raise ValueError('Remote directory symlink would escape the temporary clone: ' + rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink():
                target.unlink()
            if target.exists() and not target.is_file():
                raise ValueError('Local file conflicts with a remote directory: ' + rel)
            shutil.copy2(ROOT / rel, target)
        (checkout / 'VERSION').write_text(planned + '\n')
        git('add', '--all', cwd=checkout)
        if git('diff', '--cached', '--quiet', check=False, cwd=checkout).returncode:
            git(*identity, 'commit', '-m', f'Release RdxDownloader v{planned}', cwd=checkout, capture=False)
        git(*identity, 'tag', '-a', 'v' + planned, '-m', f'RdxDownloader v{planned}', cwd=checkout)
        git('push', '--atomic', 'origin', 'HEAD:main', 'refs/tags/v' + planned, cwd=checkout, capture=False)
    # Reflect the successful public version without changing local commit history.
    (ROOT / 'VERSION').write_text(planned + '\n')
    print('Published from the temporary clone. Original local commits and .git were preserved.')
    print('Future runs will fetch current tags and can use this same safe import mode again.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dry-run', action='store_true', help='Read local state only: no writes, fetches, commits or pushes.')
    p.add_argument('--yes', action='store_true', help='Confirm publishing after reviewing files yourself.')
    p.add_argument('--snapshot', action='store_true', help='Publish reviewed files from a fresh remote-main clone, retaining remote-only files.')
    args = p.parse_args()
    current = (ROOT / 'VERSION').read_text().strip()
    has_git = (ROOT / '.git').exists()
    tags = git('tag', '--list', 'v*').stdout.split() if has_git else []
    planned = next_version(current, tags)
    if args.dry_run:
        print(f'RdxDownloader dry run: {REPO}\nPlanned local version: v{planned}')
        print('No changes, network access, or pushes made. Actual release fetches remote state first.')
        return
    if not has_git:
        git('init', '-b', 'main')
    branch = git('branch', '--show-current').stdout.strip()
    if branch != 'main':
        raise ValueError('Switch to the intended main branch yourself before releasing; no automatic branch rename.')
    origin = remote_origin()
    identity = check_identity()
    # Fetch remote main explicitly; old configurations may have a missing/incorrect refspec.
    git('fetch', 'origin', '--tags', capture=False)
    remote_heads = git('ls-remote', '--heads', 'origin', 'refs/heads/main').stdout.strip()
    if remote_heads:
        git('fetch', 'origin', '+refs/heads/main:refs/remotes/origin/main', capture=False)
    tags = git('tag', '--list', 'v*').stdout.split()
    planned = next_version(current, tags)
    local_head = exists('HEAD')
    snapshot = bool(remote_heads) and (args.snapshot or not local_head or git('merge-base', '--is-ancestor', 'origin/main', 'HEAD', check=False).returncode != 0)
    files = project_files()
    if not confirm(planned, files, snapshot, args.yes):
        return
    if snapshot:
        publish_snapshot(origin, files, planned, identity)
    else:
        (ROOT / 'VERSION').write_text(planned + '\n')
        git('add', '--all')
        staged = git('diff', '--cached', '--name-only', '-z').stdout.split('\0')
        if any(forbidden(f) for f in staged if f):
            raise ValueError('Private/runtime paths were staged. Unstage and review them before publishing.')
        if git('diff', '--cached', '--quiet', check=False).returncode:
            git(*identity, 'commit', '-m', f'Release RdxDownloader v{planned}', capture=False)
        elif not exists('HEAD'):
            raise ValueError('No initial commit exists.')
        git(*identity, 'tag', '-a', 'v' + planned, '-m', f'RdxDownloader v{planned}')
        git('push', '--atomic', 'origin', 'HEAD:main', 'refs/tags/v' + planned, capture=False)
    print(f'Released v{planned}. Backend hosting is separate from publishing the source repository.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as e:
        print(f'Release stopped: {e}', file=sys.stderr)
        print('Your original history is not reset or force-pushed. Check the Git error above before retrying.', file=sys.stderr)
        sys.exit(1)
