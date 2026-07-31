#!/usr/bin/env bash
# testing/challenges/prove_team_collaboration_challenge.sh
#
# Slide claim: "All developers work on the same codebase. Merge conflicts
# are frequent."
#
# Simulates two developers both editing app/routers/destinations.py in
# the SAME region at the SAME time (a very normal thing to happen when
# every feature lives in one shared codebase/repo), then attempts a real
# git merge and shows the actual conflict markers git produces.
#
# Safe to run: everything happens on two throwaway branches
# (challenge-demo-dev-a / challenge-demo-dev-b) which are deleted at the
# end. Your real branch and working tree are restored exactly as they
# were before this script ran.
#
# Usage:
#   bash testing/challenges/prove_team_collaboration_challenge.sh

set -e

TARGET_FILE="app/routers/destinations.py"
ORIGINAL_BRANCH=$(git branch --show-current)
STARTING_COMMIT=$(git rev-parse HEAD)

if [ -n "$(git status --porcelain)" ]; then
  echo "You have uncommitted changes — commit or stash them first, this script switches branches."
  exit 1
fi

echo "=== Simulating two developers both touching $TARGET_FILE ==="

git checkout -q -b challenge-demo-dev-a
sed -i.bak "1i # DEV A: added a comment here while working on a search filter feature" "$TARGET_FILE"
rm -f "$TARGET_FILE.bak"
git commit -qam "Dev A: search filter tweak"
echo "Dev A committed a change on challenge-demo-dev-a"

git checkout -q "$ORIGINAL_BRANCH"
git checkout -q -b challenge-demo-dev-b
sed -i.bak "1i # DEV B: added a comment here while working on a sorting feature" "$TARGET_FILE"
rm -f "$TARGET_FILE.bak"
git commit -qam "Dev B: sorting feature"
echo "Dev B committed a DIFFERENT change to the SAME line on challenge-demo-dev-b"

echo ""
echo "=== Attempting to merge Dev A's branch into Dev B's branch ==="
if git merge challenge-demo-dev-a --no-edit -q 2>/tmp/merge_output.txt; then
  echo "(No conflict this run — try touching the exact same line number instead of both inserting at line 1.)"
else
  echo "[PROVEN] Merge conflict, exactly as the slide describes:"
  echo ""
  cat /tmp/merge_output.txt
  echo ""
  echo "--- conflict markers in $TARGET_FILE ---"
  grep -A 4 "<<<<<<<" "$TARGET_FILE" || true
  echo "---"
  git merge --abort
fi

echo ""
echo "=== Cleaning up: restoring your original branch and deleting the demo branches ==="
git checkout -q "$ORIGINAL_BRANCH"
git branch -qD challenge-demo-dev-a challenge-demo-dev-b
echo "Done. You're back on '$ORIGINAL_BRANCH' at the same commit as before ($STARTING_COMMIT)."
