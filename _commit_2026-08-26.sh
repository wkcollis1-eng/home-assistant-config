#!/usr/bin/env bash
# Run ON THE HA HOST, where /config is local disk and git actually works.
# Claude could not run this: git hangs on the H: Samba share from the Windows
# box - every variant, including plain `git status`, times out with no output
# (measured 2026-08-26; git 2.53.0 is instant on local disk, and .git is only
# 38 MB, so it is neither config nor size).
#
#   cd /config && bash _commit_2026-08-26.sh
#
# Commits ONLY. Never pushes - this is a public repo and the push is yours.
# Delete this file afterwards; it is not meant to be committed.
#
# The split follows CLAUDE.md: "NEVER commit multiple unrelated changes in one
# commit." Seven commits, each one thing.
set -u

cd /config || { echo "not /config"; exit 1; }

echo "=== branch and state ==="
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "  on branch: $BRANCH"
git status --porcelain | head -40
echo

# Never commit straight onto the default branch.
case "$BRANCH" in
  main|master)
    NEW="audit-harness-overhaul-2026-08-26"
    echo "=== on the default branch - creating $NEW ==="
    git checkout -b "$NEW" || exit 1
    ;;
  *) echo "=== already on a non-default branch, staying put ===" ;;
esac
echo

SIG="Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"

c () {   # c "<subject>" "<body>" <paths...>
  local subj="$1" body="$2"; shift 2
  local found=0
  for p in "$@"; do [ -e "$p" ] && found=1; done
  [ $found -eq 0 ] && { echo "-- skip (no files): $subj"; return; }
  git add -- "$@" 2>/dev/null
  if git diff --cached --quiet; then echo "-- skip (nothing staged): $subj"; return; fi
  git commit -q -m "$subj" -m "$body" -m "$SIG" && echo "++ $subj"
}

c "audit: fail-safe same-second contention, and ~4x faster" \
"Contention now examines every time-triggered automation (111), not just the
~20 declared in pipelines.yaml - an undeclared pair sharing a second and an
entity previously produced nothing. eod-read-write and eod-write-unmodelled
raised WARN -> FAIL: when the checker cannot prove two automations do not
collide, it blocks. Adds eod-time-unresolvable for templated trigger times.

Memoized load()/text(): 18.0s -> 3.85s min, n=5, local disk; 18.56s -> 5.68s
against the live tree, identical verdict. Verified no rule mutates a loaded
structure first.

New rules: unparseable-yaml (the audit used to die with a traceback on one
malformed file, before any rule ran), duplicate-automation-id and
duplicate-pipeline-key (PyYAML silently keeps the LAST duplicate mapping key,
so a duplicated pipeline entry ceases to exist with no error), open-question
(R14 mechanised), dashboard-not-pasted (the P12 gap). Findings now carry a
fix field, and --baseline reports NEW/FIXED/UNCHANGED." \
  scripts/ha_audit.py

c "harness: derived rule inventory, 29 rules proven, token recovery" \
"Rule-id inventory is scraped from ha_audit.py's source instead of typed.
Three hand-kept counts in CLAUDE.md had drifted and eod-concurrent had fallen
out of the accounting entirely - invisible to --list while looking considered.

Coverage 9 of 34 -> 29 of 43 testable rule ids; 20 new fault injectors.
dashboards/ added to the copied tree (it returned empty in both trees before,
so two rules were listed COVERED with their dashboard path never exercised).

Direction 1 compares (rule, message) pairs, not rule ids: a rule that already
fires for another reason previously read as 'did not fire' when it had fired
correctly. Direction 2 asserts per rule rather than demanding a finding-free
tree, so a genuine WARN in the house no longer fails the suite.

run_audit() recovers HA_TOKEN from the EXISTING ha_audit_cmd secret rather
than a second copy, and passes it by environment only - the temp trees never
receive it (verified: token value in 0 of 376 generated files)." \
  scripts/test_ha_audit.py

c "tooling: gate, pipeline generator, log stats, source fetcher" \
"gate.py - the DEFINITION OF DONE gate as one command. The verdict block is
GENERATED, which is the only reliable defence against the assurance-upgrade
failure the verdict table exists to prevent. Replaced three drifted copies of
the sequence in CLAUDE.md. Steps 3-5 stay manual (R12).

new_pipeline.py - scaffolds all four pieces of a capture pipeline from one
declaration, and refuses a trigger second where its entities would collide.
Built because stamp-not-snapshotted (130) and unguarded-shell-command (111)
were the two most-fired rules across 38 nightly runs - 241 of ~500 findings,
both boilerplate omissions, every one a round trip.

audit_log_stats.py - crosses the nightly log against harness coverage. A rule
that has never fired AND has no injector is one whose silence proves nothing.

ha_source.py - fetches HA core source at the pinned .HA_VERSION and caches it,
so R6 stops costing a hand-built URL.

check_provenance.py now times out at 30s and names --all: its default git mode
cannot complete over Samba at all." \
  scripts/gate.py scripts/new_pipeline.py scripts/audit_log_stats.py \
  scripts/ha_source.py scripts/check_provenance.py .gitignore

c "packages/audit: UI actions and a contention indicator" \
"Developer Tools > Actions entries for the whole toolchain: ha_run_all_checks,
ha_gate, ha_audit_log_stats, ha_provenance, ha_gen_reference (defaults to
--check; writing is an explicit toggle). Each carries the ha_maintenance_mode
guard and returns the raw service response rather than round-tripping stdout
through a script variable, which is what broke from_json on 2026-08-22.

binary_sensor.ha_eod_contention plus its counter, separate from
ha_audit_failing: contention is the only failure class that corrupts DATA
rather than reporting, so it gets its own light.

new_pipeline.py deliberately NOT exposed - it is the only script that mutates
automations.yaml." \
  packages/audit.yaml

c "hooks: blocking Stop gate, PostToolUse validator, drift check" \
"Tracked source for the hooks that run from ~/.claude/hooks on the Windows box.

The Stop gate could not stop anything - it emitted systemMessage only. It now
returns decision: block, standing down after two consecutive blocks, and
refuses to block at all when it cannot persist the retry count (which would
otherwise wedge a session forever). It now also watches dashboards/, which it
did not - dashboard edits silently skipped the gate.

ha_validate_edit.py validates the file just edited, so a YAML error lands next
to the edit instead of at the end of the turn.

deploy_drift() compares the deployed hook against this tracked copy at every
session start. The hooks run from C: on purpose: a guard living on the drive
it guards cannot report that drive missing." \
  .claude/hooks/ha_guard.py .claude/hooks/ha_audit_gate.py \
  .claude/hooks/ha_validate_edit.py .claude/settings.json

c "docs: regenerate ENTITIES/AUTOMATIONS/PACKAGES" \
"Written by scripts/gen_reference.py after the new package entities registered." \
  ENTITIES.md AUTOMATIONS.md PACKAGES.md

c "docs: record the corrections this work produced" \
"CLAUDE.md: HA_URL does not enable the live check, HA_TOKEN does - it was
true-by-accident only because HA_TOKEN is a persistent env var. git on H: does
not merely refuse, it hangs. The hooks and settings live in ~/.claude, not a
project file, because the project root IS C:\\Users\\wkcol - moving them under
H: silently disabled every hook and deny rule. Deny rules are evaluated BEFORE
hooks, so ha_guard.py is the backstop, not the primary, plus how to test a
deny rule (claude doctor will not tell you). The KNOWN ISSUES 23:58:00
collision entry was stale and is marked so rather than deleted (R13).

CHANGELOG: the [2026.08.26] section, including the end-to-end guard test where
all five guards were proven through their real path for the first time." \
  CLAUDE.md CHANGELOG.md

echo
echo "=== result ==="
git --no-pager log --oneline -8
echo
echo "NOT PUSHED. This is a public repo - review with:"
echo "    git show --stat HEAD~6..HEAD"
echo "then push yourself when you are happy."
echo "Afterwards: rm /config/_commit_2026-08-26.sh"
