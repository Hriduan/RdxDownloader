#!/usr/bin/env bash
# One-time setup on YOUR device. This website never receives GitHub credentials.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if ! command -v gh >/dev/null 2>&1; then
  if command -v pkg >/dev/null 2>&1; then pkg install git python gh; else echo 'Install the official GitHub CLI (gh), then run this script again.' >&2; exit 1; fi
fi
if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  printf 'Authorize GitHub once in your own browser using its device code. No password belongs in this project.
'
  printf 'GitHub CLI normally uses OS credential storage; without a keyring it can fall back to a token file.
'
  printf 'If that is unacceptable, stop and use SSH with your OS agent instead. Never commit auth files.
'
  gh auth login --hostname github.com --git-protocol https --web
fi
gh auth setup-git --hostname github.com
if [[ ! -e .git ]]; then git init -b main; fi
if ! git config user.name >/dev/null; then git config user.name "$(gh api user --jq '.login')"; fi
if ! git config user.email >/dev/null; then git config user.email "$(gh api user --jq '"\(.id)+\(.login)@users.noreply.github.com"')"; fi
printf 'Setup done. Use bash update; no RELEASE word is required. Authentication can still expire or be revoked.
'
