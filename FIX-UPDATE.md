# Complete-package fix, v1.0.1

This is **not** the earlier small patch ZIP. This archive includes every website, backend, test, guide and workflow file. Extract the single RdxDownloader folder, then merge its contents into the intended project root. Preserve `.git`, private configuration and your own newer work. Read docs/TERMUX.md first.

The screenshot's history mismatch is handled by the included safe snapshot publisher: a fresh temporary clone is based on remote main, reviewed local files are copied in, and a normal commit/tag is pushed. There is no destructive reset, credential storage or force push. Remote-only files remain; same-named remote files can be replaced by your reviewed local copies.

```bash
bash update --dry-run
bash update
```

Backend startup is a separate action:

```bash
bash scripts/setup-termux.sh  # native supported 64-bit Termux only
bash start                  # open http://127.0.0.1:8080 on the same phone
```

For public hosting, use the Docker backend in docs/DEPLOYMENT.md. GitHub Pages alone cannot execute the downloader. No source upload or Git fix can change that hosting limitation.
