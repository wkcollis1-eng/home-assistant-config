# dashboards

_Moved verbatim from CLAUDE.md (CONSTRAINTS, dashboards corollary) on 2026-10-25; the pointer left there names this file._

**`dashboards/` is a SOURCE copy HA never loads.** No `lovelace:` block includes it;
live dashboards are UI-managed in `.storage/lovelace.*` (off-limits), so no file
edit changes what Bill sees.

| dir | is | hand-edit? |
|---|---|---|
| `dashboards/views/` | hand-kept; may be AHEAD of live | **YES** - not-yet-live corrections go here |
| `dashboards/cards/` | snippet library | yes |
| `dashboards/lovelace/` | GENERATED mirror of live | **NO** - re-run `HA_CONFIG='H:/' python scripts/export_dashboards.py` after a paste |

Workflow: write `dashboards/views/<name>.yaml` (single-view format), hand Bill the
exact YAML to paste into the raw configuration editor, say it is not live until he
does, then re-run `export_dashboards.py`. **Never remove or loosen a deny rule to
make an edit possible** - find the file you may edit instead.
*Why: 2026-08-23 a card read a superseded sensor with every gate passing;
2026-09-14 a session hand-edited `lovelace/` and had a deny rule removed.*

