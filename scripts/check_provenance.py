#!/usr/bin/env python
"""R17 gate - no naked ratios. See CLAUDE.md R17.

Targets COMPARATIVE claims, which is what R17 is actually about:
  - multipliers   "2.18x", "0.24x"   - almost always a rate against a baseline
  - percentages carrying comparative language ("up 12%", "27.7% vs 19.3%")
It deliberately does NOT flag bare percentages in tables or sensor readings -
those are [M] values, and a gate that fires on them trains you to skim.

  python scripts/check_provenance.py            # ADDED lines vs HEAD (default)
  python scripts/check_provenance.py --all F..  # whole files (audit mode)

Exit 0 clean, 1 if anything fired.
"""
import re, subprocess, sys, pathlib
NL = chr(10)

try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception: pass

MULT = re.compile(r'(?<![\w.])(\d{1,2}(?:\.\d+)?)\s*[x×](?![\w\d])')
CMP  = re.compile(r'\b(up|down|vs\.?|versus|better|worse|improv\w*|gain\w*|lost|loss|'
                  r'rose|fell|rise|fall\w*|higher|lower|beat\w*|against)\b', re.I)
PCT  = re.compile(r'(?<![\w.])\d+\.?\d*\s*%')
EVIDENCE = re.compile(
    r'\bn\s*=|\bN\s*=|\bz\s*=|\bP\s*[=<(]|\bp\s*[=<]|\bchi|\bsd\b|\bCI\b'
    r'|\d+\s*/\s*\d+|\bof\s+[\d,]|\bin\s+[\d,]|\bover\s+[\d,]'
    r'|\bframes\b|\bslots\b|\bsamples\b|\bgaps\b|\bmin\b|\bhours?\b'
    r'|\[M\]|\[S\]|\[D\]|\[I\]')
SKIP = re.compile(r'^\s*[-=!#*_]{3,}\s*$|^\s*$')
WATCH = ('.md', '.yaml', '.yml')

def added_lines():
    # GIT ON H: IS PATHOLOGICAL. Measured 2026-08-25 over the Samba share: a
    # bare `git ls-files --error-unmatch` did not return inside 2 minutes, and
    # a `git diff HEAD` was still running after 30. So the DEFAULT mode of this
    # script - the one CLAUDE.md's session protocol documents - could not
    # complete off-host at all, which left R15-R18 (the newest and least
    # mechanised rules) with a gate that never ran in the environment it was
    # written for. Fail fast and name the mode that does work, rather than
    # hanging until somebody kills it.
    GITFREE = 'python scripts/check_provenance.py --all <edited files>'
    try:
        out = subprocess.run(['git', '-c', 'safe.directory=*', 'diff', '-U0', 'HEAD', '--'],
                             capture_output=True, text=True, encoding='utf-8',
                             errors='replace', timeout=30).stdout
    except (subprocess.TimeoutExpired, OSError) as exc:
        sys.stderr.write(
            'check_provenance: git diff did not complete (%s).%s'
            '  Expected on H: over Samba. Use the git-free mode:%s'
            '      %s%s' % (type(exc).__name__, NL, NL, GITFREE, NL))
        sys.exit(2)
    path, ln, rows = None, 0, []
    for line in out.splitlines():
        if line.startswith('+++ b/'): path = line[6:]; continue
        m = re.match(r'@@ -\d+(?:,\d+)? \+(\d+)', line)
        if m: ln = int(m.group(1)); continue
        if line.startswith('+') and not line.startswith('+++'):
            if path and path.endswith(WATCH): rows.append((path, ln, line[1:]))
            ln += 1
    return rows

def check(rows):
    hits = []
    for path, ln, text in rows:
        if SKIP.match(text) or EVIDENCE.search(text): continue
        why = None
        if MULT.search(text): why = "multiplier with no n / test / tag"
        elif PCT.search(text) and CMP.search(text): why = "comparative % with no n / test / tag"
        if why: hits.append((path, ln, why, text.strip()[:90]))
    return hits

if __name__ == '__main__':
    if '--all' in sys.argv:
        fs = [a for a in sys.argv[1:] if a != '--all']
        rows = [(f, i, t) for f in fs for i, t in enumerate(
            pathlib.Path(f).read_text(encoding='utf-8', errors='replace').splitlines(), 1)]
    else:
        rows = added_lines()
    hits = check(rows)
    for p, i, why, t in hits: print(f"WARN provenance {p}:{i}  {why}:  {t}")
    print(f"{len(hits)} WARN   [R17 - no naked ratios; an R15 tag satisfies it]")
    sys.exit(1 if hits else 0)
