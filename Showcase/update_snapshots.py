#!/usr/bin/env python3
"""
Grafana Snapshot Automation for GitHub Showcase

This script:
1. Fetches dashboards from Grafana
2. Creates public snapshots on snapshots.raintank.io
3. Updates README.md with snapshot URLs
4. Optionally commits and pushes to GitHub

Prerequisites:
- Grafana API key with Viewer permissions (or admin credentials)
- Git configured for push access (if auto-commit enabled)

Usage:
    python update_snapshots.py

Environment Variables:
    GRAFANA_URL      - Grafana base URL (default: http://localhost:3000)
    GRAFANA_API_KEY  - API key for authentication
    GITHUB_PUSH      - Set to "true" to auto-commit and push
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path

# Optional imports - script will guide user if missing
try:
    import requests
except ImportError:
    print("ERROR: 'requests' module required. Install with: pip install requests")
    exit(1)

# Configuration
GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3000")
GRAFANA_API_KEY = os.environ.get("GRAFANA_API_KEY", "")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "admin")
GRAFANA_PASS = os.environ.get("GRAFANA_PASS", "admin")
GITHUB_PUSH = os.environ.get("GITHUB_PUSH", "false").lower() == "true"

SCRIPT_DIR = Path(__file__).parent
README_PATH = SCRIPT_DIR / "README.md"

# Dashboards to snapshot with their panel selections
# Format: "snapshot_id": {"uid": "dashboard_uid", "title": "Display Title", "panels": [panel_ids] or None for full}
DASHBOARDS = {
    "energy_overview": {
        "uid": "energy",
        "title": "Energy Overview",
        "panels": None,  # Full dashboard
        "expires": 86400 * 7,  # 7 days
    },
    "daily_energy": {
        "uid": "energy",
        "title": "Daily Energy by Circuit",
        "panels": None,
        "expires": 86400 * 7,
    },
    "hvac_performance": {
        "uid": "energy",
        "title": "HVAC Performance",
        "panels": None,
        "expires": 86400 * 7,
    },
    "spc_monitoring": {
        "uid": "spc-appliances",
        "title": "SPC Monitoring",
        "panels": None,
        "expires": 86400 * 7,
    },
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_grafana_session():
    """Create a requests session with Grafana authentication."""
    session = requests.Session()

    if GRAFANA_API_KEY:
        session.headers["Authorization"] = f"Bearer {GRAFANA_API_KEY}"
    else:
        # Fall back to basic auth
        session.auth = (GRAFANA_USER, GRAFANA_PASS)

    return session


def get_dashboard(session, uid):
    """Fetch a dashboard by UID."""
    url = f"{GRAFANA_URL}/api/dashboards/uid/{uid}"

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch dashboard {uid}: {e}")
        return None


def create_snapshot(session, dashboard_data, title, expires=86400):
    """
    Create a public snapshot on snapshots.raintank.io.

    Args:
        session: Authenticated requests session
        dashboard_data: Dashboard JSON from Grafana API
        title: Snapshot title
        expires: Expiration time in seconds (default 24 hours)

    Returns:
        Snapshot URL or None on failure
    """
    url = f"{GRAFANA_URL}/api/snapshots"

    payload = {
        "dashboard": dashboard_data.get("dashboard", dashboard_data),
        "name": title,
        "expires": expires,
        "external": True,  # Publish to raintank.io for public access
    }

    try:
        response = session.post(url, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()

        # External snapshots return a different URL
        snapshot_url = result.get("url", result.get("externalUrl"))
        logger.info(f"Created snapshot: {snapshot_url}")
        return snapshot_url

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create snapshot: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text}")
        return None


def update_readme(snapshot_urls):
    """
    Update README.md with new snapshot URLs.

    Replaces content between <!-- SNAPSHOT:id --> and <!-- /SNAPSHOT:id --> markers.
    """
    if not README_PATH.exists():
        logger.error(f"README not found: {README_PATH}")
        return False

    content = README_PATH.read_text(encoding="utf-8")

    for snapshot_id, url in snapshot_urls.items():
        if url:
            # Create the embedded snapshot markdown
            title = DASHBOARDS.get(snapshot_id, {}).get("title", snapshot_id)
            replacement = f"[![{title}]({url})]({url})"

            # Replace between markers
            pattern = rf"(<!-- SNAPSHOT:{snapshot_id} -->).*?(<!-- /SNAPSHOT:{snapshot_id} -->)"
            content = re.sub(
                pattern,
                rf"\1\n{replacement}\n\2",
                content,
                flags=re.DOTALL
            )

    # Update timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = re.sub(
        r"(<!-- LAST_UPDATED -->).*?(<!-- /LAST_UPDATED -->)",
        rf"\1{timestamp}\2",
        content
    )

    README_PATH.write_text(content, encoding="utf-8")
    logger.info(f"Updated {README_PATH}")
    return True


def git_commit_and_push():
    """Commit and push README changes to GitHub."""
    import subprocess

    try:
        # Stage the README
        subprocess.run(
            ["git", "add", str(README_PATH)],
            cwd=SCRIPT_DIR,
            check=True,
            capture_output=True
        )

        # Commit
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            ["git", "commit", "-m", f"Update Grafana snapshots ({timestamp})"],
            cwd=SCRIPT_DIR,
            check=True,
            capture_output=True
        )

        # Push
        subprocess.run(
            ["git", "push"],
            cwd=SCRIPT_DIR,
            check=True,
            capture_output=True
        )

        logger.info("Pushed changes to GitHub")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed: {e}")
        return False


def main():
    """Main entry point."""
    logger.info("Starting Grafana snapshot update")
    logger.info(f"Grafana URL: {GRAFANA_URL}")

    session = get_grafana_session()

    # Test connection
    try:
        response = session.get(f"{GRAFANA_URL}/api/health", timeout=10)
        response.raise_for_status()
        logger.info("Grafana connection successful")
    except requests.exceptions.RequestException as e:
        logger.error(f"Cannot connect to Grafana: {e}")
        logger.error("Check GRAFANA_URL and credentials")
        return 1

    snapshot_urls = {}

    for snapshot_id, config in DASHBOARDS.items():
        logger.info(f"Processing: {config['title']}")

        # Fetch dashboard
        dashboard_data = get_dashboard(session, config["uid"])
        if not dashboard_data:
            continue

        # Create snapshot
        url = create_snapshot(
            session,
            dashboard_data,
            config["title"],
            config.get("expires", 86400)
        )

        snapshot_urls[snapshot_id] = url

    # Update README
    if any(snapshot_urls.values()):
        update_readme(snapshot_urls)

        if GITHUB_PUSH:
            git_commit_and_push()
    else:
        logger.warning("No snapshots created successfully")
        return 1

    logger.info("Snapshot update complete")
    return 0


if __name__ == "__main__":
    exit(main())
