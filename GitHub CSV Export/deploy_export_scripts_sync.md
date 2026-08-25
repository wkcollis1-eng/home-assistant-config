# Deploy: GitHub CSV Export + Lifepo4 Export scripts

## Context
Two export directories in the repo contain scripts that must match
the live files under `/config/scripts/`. This is an idempotent sync —
deploy if source differs from target, skip if identical.

Source → Target mappings:
  "Lifepo4 Export/lifepo4_export.py"     → /config/scripts/lifepo4_export.py
  "GitHub CSV Export/csv_manager.py"     → /config/scripts/csv_manager.py
  "GitHub CSV Export/push_csv_to_github.py" → /config/scripts/push_csv_to_github.py

## Task

For each of the three file pairs above:

1. Read the source file from the repo.
2. Read the target file from `/config/scripts/` (may not exist yet).
3. Compare. If identical, mark SKIP. If different (or target missing), write source → target and mark DEPLOYED.
4. After all three: report a summary table:

   | File                   | Action   | Lines |
   |------------------------|----------|-------|
   | lifepo4_export.py      | DEPLOYED | N     |
   | csv_manager.py         | SKIP     | N     |
   | push_csv_to_github.py  | SKIP     | N     |

5. For lifepo4_export.py specifically, run these post-deploy checks on
   the deployed file and report PASS/FAIL for each:
   - `from zoneinfo import ZoneInfo` present
   - `HA_TZ = ZoneInfo("America/New_York")` present
   - `read_last_csv_timestamp` NOT present
   - `_bucket_sort_key` present
   - `cutoff_dt` NOT present

## Constraints
- YAML snippet files are reference docs only — do NOT deploy them:
    automations_snippet.yaml, configuration_snippet.yaml,
    github_csv_push_ha_config.yaml, utility_monthly_ha_snippets.yaml,
    GITHUB_CSV_PUSH_README.md
- Do not modify any other file under /config/scripts/.
- Do not reload HA — operator will handle that after review.
