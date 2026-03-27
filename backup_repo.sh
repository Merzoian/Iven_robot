#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

branch="$(git rev-parse --abbrev-ref HEAD)"

if [[ $# -gt 0 ]]; then
  message="$*"
else
  message="Backup $(date '+%Y-%m-%d %H:%M:%S')"
fi

git add -A

if git diff --cached --quiet; then
  echo "No changes to commit."
else
  git commit -m "$message"
fi

git push origin "$branch"

echo "Backup complete on branch '$branch'."
