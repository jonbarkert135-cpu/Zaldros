#!/bin/sh
# Publish one job's evidence (screenshots, logs, step exit codes) to its own ci-logs-* branch.
#
# The evidence branches are the only way anyone without repository admin rights can read what a CI
# job saw, so this step must not be the thing that turns a good run red — and must not hide a real
# failure either. Two runs overlapping on main both force-push the same branch, and GitHub rejects
# the loser with
#
#     ! [remote rejected] ci-logs-boot-services-mid (cannot lock ref …: is at X but expected Y)
#
# which is how iso run 33161289986 went red while every build and every boot had passed. A lost
# ref race is not a defect in Zaldros: retry it. Anything still failing after the last attempt is
# reported and exits non-zero.
#
# Usage: publish-evidence.sh <dir> <branch> <label>
# Env:   EVIDENCE_REMOTE   push URL, may carry a token — it is never echoed
#        EVIDENCE_ATTEMPTS number of push attempts (default 5)
#        EVIDENCE_SLEEP    seconds between attempts (default 3)
set -eu

DIR="${1:?usage: publish-evidence.sh <dir> <branch> <label>}"
BRANCH="${2:?branch}"
LABEL="${3:?label}"
REMOTE="${EVIDENCE_REMOTE:?EVIDENCE_REMOTE must hold the push URL}"
ATTEMPTS="${EVIDENCE_ATTEMPTS:-5}"
SLEEP="${EVIDENCE_SLEEP:-3}"

# Never let a URL with a token reach the log, whatever git decides to print.
scrub() { sed -E 's#(https?://)[^@[:space:]]*@#\1#g'; }

if [ ! -d "$DIR" ]; then
  # A build that died before writing anything still has to say so on its branch: an empty
  # commit with the label beats a red publish step that explains nothing.
  mkdir -p "$DIR"
  echo "no evidence directory was produced by this job — the job failed before writing any" \
    > "$DIR/NOTE.txt"
fi

cd "$DIR"
if command -v mogrify >/dev/null 2>&1; then
  # QEMU writes PPM screendumps; nothing renders those in a browser.
  mogrify -format png ./*.ppm 2>/dev/null && rm -f ./*.ppm || true
fi
printf '%s\n' "$LABEL" > RUN.txt

rm -rf .git
git init -q .
git checkout -q -b "$BRANCH"
git config user.email "ci@zaldros.invalid"
git config user.name "zaldros ci"
git add -A
git commit -q --allow-empty -m "$LABEL"
git remote add evidence "$REMOTE"

attempt=1
while [ "$attempt" -le "$ATTEMPTS" ]; do
  if out="$(git push -f evidence "$BRANCH" 2>&1)"; then
    echo "published $BRANCH on attempt $attempt/$ATTEMPTS"
    printf '%s\n' "$out" | scrub
    exit 0
  fi
  echo "attempt $attempt/$ATTEMPTS to publish $BRANCH failed:"
  printf '%s\n' "$out" | scrub
  attempt=$((attempt + 1))
  [ "$attempt" -le "$ATTEMPTS" ] && sleep "$SLEEP"
done

echo "could not publish $BRANCH after $ATTEMPTS attempts — the evidence for this job is only in" \
     "the job artifact"
exit 1
