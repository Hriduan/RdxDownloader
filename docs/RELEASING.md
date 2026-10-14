# Versions and the update file — ZIP-import fix

The project starts at **v1.0.0**, then v1.0.1, v1.0.2 and so on. VERSION stores the version without the v prefix. The helper targets https://github.com/Hriduan/RdxDownloader and uses your existing secure Git authentication. It does not save passwords or tokens.

```bash
bash update --dry-run  # local read-only preview; no fetch, commit or push
bash update            # fetch state, review files and type RELEASE to publish
# Without Bash:
python scripts/release.py
```

## The Termux error this fixes

The previous script stopped with:

```text
Remote main is not an ancestor of HEAD. Pull/reconcile histories first; no force push is used.
```

This can happen when you initialize a fresh local Git repository in an extracted ZIP but GitHub already has a README/commit, when your local branch has no commits yet, or when local and remote histories have diverged. It does not mean the downloader backend is broken.

## Two safe publishing modes

### Normal checkout

If local HEAD already includes remote main, the helper reviews/stages project changes, commits when needed, creates a new annotated version tag and atomically pushes main and that tag. It never rewrites remote history or forcibly replaces a tag.

### ZIP import / unrelated history / remote ahead

If remote main is not an ancestor of local HEAD (or local HEAD does not exist), the helper:

1. Lists the local publishable file snapshot and explains the replacement behavior.
2. Asks you to type RELEASE before publishing.
3. Creates a fresh temporary clone of the actual remote main.
4. Copies local nonignored project files into that clone. **Same-named remote files are replaced by your local copies**; make sure your local folder contains the version you intend to publish.
5. Keeps remote-only files, commits the snapshot on top of current remote main, creates the version tag, and pushes main + that tag atomically.
6. Deletes only its temporary clone, then updates the original local VERSION after a successful push.

Your original `.git`, local commits, index and source files are not reset, merged, checked out or cleaned by snapshot mode. No `reset --hard`, forced push, automatic conflict resolution or deletion of your original repository is used. The local checkout can retain its original unrelated history; future runs can use the same import mode again.

**Important:** Snapshot mode is file publishing, not a Git-history merge. Local-only commits are not individually imported into GitHub. Remote-only files are retained, so local deletions are not propagated. Existing remote changes at copied paths can be replaced by the local snapshot. Use a conventional clone/merge workflow if you need to preserve individual local commits, resolve conflicting edits, or intentionally delete remote files. Cancellation stops before staging/committing/pushing (initialization/fetch may already have occurred).

Ignored local files are skipped, including private .env files. Common tracked private/runtime paths are rejected before publishing. Source symlinks are not copied. Repository-local Git author identity is passed to the temporary commit without changing global configuration.

## Termux checklist

```bash
pkg install git python
cd ~/storage/downloads/RdxDownloader/RdxDownloader
bash update --dry-run
bash update
```

Use the actual project folder containing index.html, VERSION, update and scripts/release.py. If the helper says Git identity is missing, set your own non-secret name/email first:

```bash
git config user.name "YOUR NAME"
git config user.email "YOUR GITHUB EMAIL"
```

GitHub must allow your account to push to this repository. Use an existing secure Git/SSH credential method. Do not paste account passwords or tokens into source files or chat. Authentication, branch protections, repository rules and network errors can still require your action; the helper does not bypass them.

## Tags, failures and recovery

- The first available initial version is v1.0.0. Existing version tags are fetched before choosing the next patch. If your current version is already tagged, the patch increments (v1.0.9 → v1.0.10).
- Edit VERSION to an unused minor/major version if intentionally making that kind of release.
- A failed **snapshot-mode** push leaves the original checkout and VERSION intact; no remote branch/tag is changed when an atomic push is rejected. You can fix the reported access/rule/network problem and review a retry.
- A failed **normal-mode** push can leave a new local commit and tag. Inspect `git status` and `git log` before retrying; push the already-created tag/commit deliberately after correcting the problem. Never use force push as a shortcut.
- The dry-run is local only. It cannot promise a final remote-derived version or verify GitHub access.
- The GitHub tag workflow packages a source ZIP. Publishing source does not deploy the Python/FFmpeg backend. Backend hosting remains separate.

## Verification of this fix

Eight additional local-Git regression scenarios passed: unrelated committed histories, no local commits, repeated imports/version increment, cancellation, a conventional clone, rejected atomic pushes, a read-only dry-run and private-path guards. Together with existing tests, **30 Python tests passed**. Tests used temporary local repositories only; no real GitHub push was attempted.

## v1.0.1 complete package

The shipped version is 1.0.1. Actual releases fetch remote tags and choose a version higher than the highest published semantic version if needed, even when the extracted VERSION is older. `bash update --snapshot` explicitly uses a temporary clone of remote main; automatic mode uses it for unrelated/behind local history. Only remote-tracking refs may be refreshed with a leading + in fetch; no force push is made to GitHub. See TERMUX.md for the screenshot recovery steps.
