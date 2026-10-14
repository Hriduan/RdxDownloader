# v1.0.2 publishing fix

`bash update` now supplies the publishing confirmation automatically. `bash update --review` retains the old review prompt. The safe imported-ZIP publisher, atomic push and no-force-push rules remain.

Your own phone must authorize GitHub once with `bash scripts/setup-github.sh` unless its Git credentials and author identity already work. The helper does not collect passwords. GitHub CLI storage and token expiry still apply. Never put a token in a repository URL, config.js or this ZIP.

A release publishes source. The already-created Render service automatically rebuilds main after successful commits. A failed push is not a successful deployment. Check the Render dashboard and live `/api/health` after updating. See START-HERE.md.
