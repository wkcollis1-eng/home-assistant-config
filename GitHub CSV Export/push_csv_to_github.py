#!/usr/bin/env python3
"""
push_csv_to_github.py  —  Home Assistant → GitHub CSV uploader
================================================================
Pushes all CSV report files from /config/reports/ to the
wkcollis1-eng/Residential-HVAC-Performance-Baseline- repository
under homeassistant/reports/ using the GitHub REST API.

Files pushed:
  hvac_daily_YYYY.csv      — daily HVAC row (appended nightly)
  hvac_monthly.csv         — HVAC monthly summary (appended end of month)
  hvac_setback_log.csv     — setback events (event-driven)
  input_number_backup.csv  — input_number snapshot (weekly)
  utility_monthly.csv      — utility billing + runtime snapshot (end of month)

Files land in homeassistant/reports/ — deliberately separated from
the curated historical datasets in data/ which have different schemas
and are maintained manually.

No git binary required; runs cleanly inside the HA container using
only Python standard-library modules.

Usage (via shell_command):
    python3 /config/scripts/push_csv_to_github.py

Environment / args:
    GITHUB_TOKEN  — personal access token (repo scope)
                    passed by shell_command from secrets.yaml

Exit codes:
    0  — all files pushed successfully (or unchanged)
    1  — one or more files failed

Author: generated for wkcollis1-eng/Residential-HVAC-Performance-Baseline-
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ──────────────────────────────────────────────────────────────────
# Configuration — edit REPO / BRANCH if the repo ever moves
# ──────────────────────────────────────────────────────────────────
OWNER      = "wkcollis1-eng"
REPO       = "Residential-HVAC-Performance-Baseline-"
BRANCH     = "main"
API_BASE   = "https://api.github.com"
CONFIG_DIR = Path("/config")

# Files to push: local path (relative to CONFIG_DIR) → GitHub path
#
# HA CSV exports land under homeassistant/reports/ — intentionally
# separate from data/ which holds the curated historical datasets
# with different schemas (monthly_summary.csv, daily_temperature.csv,
# etc.).  Do not point these at data/ paths.
#
# The daily CSV filename is year-dynamic.
YEAR = datetime.now().year
FILES_TO_PUSH = {
    f"reports/hvac_daily_{YEAR}.csv":   f"homeassistant/reports/hvac_daily_{YEAR}.csv",
    "reports/hvac_monthly.csv":         "homeassistant/reports/hvac_monthly.csv",
    "reports/hvac_setback_log.csv":     "homeassistant/reports/hvac_setback_log.csv",
    "reports/input_number_backup.csv":  "homeassistant/reports/input_number_backup.csv",
    "reports/utility_monthly.csv":      "homeassistant/reports/utility_monthly.csv",
}

# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    """Timestamped stdout log — captured by HA logger."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[push_csv_to_github] {ts}  {msg}", flush=True)


def github_request(token: str, method: str, path: str,
                   body: dict | None = None) -> dict:
    """
    Make a GitHub API request and return the parsed JSON response.
    Raises urllib.error.HTTPError on 4xx/5xx.
    """
    url = f"{API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent":    "ha-csv-pusher/1.0",
    }
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=headers,
                                  method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def get_file_sha(token: str, repo_path: str) -> str | None:
    """
    Return the blob SHA of an existing file in the repo, or None if
    the file does not yet exist.  Required by the GitHub Contents API
    for updates.
    """
    api_path = f"/repos/{OWNER}/{REPO}/contents/{repo_path}?ref={BRANCH}"
    try:
        data = github_request(token, "GET", api_path)
        return data.get("sha")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None          # File does not exist yet — will be created
        raise


def push_file(token: str, local_path: Path, repo_path: str) -> bool:
    """
    Push one file to GitHub.  Returns True on success, False on failure.
    Skips gracefully if the local file is missing.
    """
    if not local_path.exists():
        log(f"SKIP  {local_path.name} — file not found locally")
        return True             # Not a push error; skip silently

    content_bytes  = local_path.read_bytes()
    content_b64    = base64.b64encode(content_bytes).decode()

    sha = get_file_sha(token, repo_path)

    commit_msg = (
        f"auto: update {local_path.name} "
        f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}]"
    )

    body: dict = {
        "message": commit_msg,
        "content": content_b64,
        "branch":  BRANCH,
    }
    if sha:
        body["sha"] = sha       # Required for updates; omit for creates

    api_path = f"/repos/{OWNER}/{REPO}/contents/{repo_path}"
    try:
        result = github_request(token, "PUT", api_path, body)
        commit_sha = result.get("commit", {}).get("sha", "?")[:7]
        action     = "updated" if sha else "created"
        log(f"OK    {repo_path}  [{action}]  commit={commit_sha}")
        return True
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode() if hasattr(exc, "read") else str(exc)
        log(f"FAIL  {repo_path}  HTTP {exc.code}: {err_body}")
        return False


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────

def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        log("ERROR  GITHUB_TOKEN environment variable is not set.")
        return 1

    log(f"Starting push of {len(FILES_TO_PUSH)} CSV file(s) → "
        f"{OWNER}/{REPO}@{BRANCH}")

    failures = 0
    for local_rel, repo_rel in FILES_TO_PUSH.items():
        local_abs = CONFIG_DIR / local_rel
        ok = push_file(token, local_abs, repo_rel)
        if not ok:
            failures += 1

    if failures == 0:
        log(f"Done — all files pushed successfully.")
    else:
        log(f"Done — {failures} file(s) FAILED.")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
