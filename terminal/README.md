# WarSignal Terminal

A Bloomberg-terminal-style web UI (Flask + plain HTML/JS, no frameworks, no
game art) for monitoring WarSignal missions from the `missions/` folder.
Dark monospace theme, dense tables, full keyboard navigation.

```bash
python main.py terminal                      # http://127.0.0.1:8020
python main.py terminal --port 8020 --host 127.0.0.1
python main.py terminal --no-pull            # skip git pulls
python main.py terminal --pull-interval 30   # pull every 30 s
python main.py terminal --no-pull --snapshot snap.html
```

## How the pull loop works

GitHub `main` is the source of truth. A daemon thread calls
`Monitor.refresh()` every `--pull-interval` seconds (default 60): each
refresh runs `git pull --rebase --autostash` in the repo root (skipped with
`--no-pull`), then re-reads `missions/status/*.json`,
`missions/runs/*` (+ `INDEX.md`), `missions/results.csv`,
`missions/queue.txt`, `missions/failed.txt`, and `missions/config.json`.
Run-folder reads are cached by directory/manifest mtime, so 200+ runs
re-scan in well under a second. `GET /api/state?refresh=1` forces a refresh;
the browser polls `/api/state` every 5 s and shows the seconds until the
next pull in the ticker.

## Panes and keys

| Key | Pane |
| --- | ---- |
| `1` | ACTIVE — live `missions/status/*.json` entries with stage, ticking elapsed, progress bar coloured by `signal` (red→green), last message, Devin session links |
| `2` | QUEUE — `missions/queue.txt` entries with position, round, parent |
| `3` | HISTORY — one row per run folder; click a header to sort; `Enter`/click opens a detail pane (stats, judge scores, trade idea, `viz.png`, rendered `note.md`) |
| `4` | LEADERBOARD — ok runs ranked by validity then permutation p |
| `5` | LOG — status file diffs: appeared / changed stage/progress/message / removed |

Global: `j`/`k`/arrow keys move the row highlight, `Enter` opens detail,
`Esc` closes detail (or clears the filter), `/` focuses the filter input
(substring match over the current pane), `r`/`F5` forces a server refresh.

## `/api/state` shape

```json
{
  "generated_at": "…", "generated_ts": 0.0,
  "pull_interval": 60.0, "pull_enabled": true,
  "git": {"head": "abc1234", "branch": "main", "last_pull_at": "…",
          "last_pull_ok": true, "pull_output": "…"},
  "config": {"max_agents": 5},
  "counts": {"running": 3, "queued": 97, "done": 118, "failed": 10},
  "active": [status…], "statuses": [status…],
  "queue": [{"position": 1, "round": "", "parent_id": "", "hypothesis": "…"}],
  "runs": [{"folder": "…", "mission_id": "…", "status": "ok", "n": 378,
            "r": 0.15, "effect": 0.15, "best_lag": 0, "perm_p": 0.02,
            "bonferroni_p": 0.33, "bonferroni_ok": false, "validity": 6.02,
            "interestingness": 4.22, "unexpectedness": 5.16,
            "actionability": null, "signal": 0.6, "trade_idea": null,
            "has_viz": true, "has_note": true}],
  "leaderboard": [{"rank": 1, "mission_id": "…", "validity": 9.1,
                   "effect": 0.4, "perm_p": 0.001, "trade_idea": {…}}],
  "failed": [{"hypothesis": "…", "error": "…"}],
  "log": [{"at": "…", "mission_id": "…", "kind": "changed", "field": "stage",
           "old": "stats", "new": "viz", "message": "…"}]
}
```

`GET /api/run/<folder>` returns full run detail including `note_md`;
`GET /runs/<folder>/<file>` serves files directly inside a run folder
(`viz.png`, `note.md`, JSON). Folder names are validated against the run-dir
pattern and path traversal is rejected.

## Queue line prefixes

`missions/queue.txt` lines may carry an optional bracket prefix:

```text
[<round>] <hypothesis>
[<round> <- <parent_mission_id>] <hypothesis>
<round>\t<parent_mission_id>\t<hypothesis>
<hypothesis>
```

## Snapshots

`--snapshot PATH` builds the state once (pulling unless `--no-pull`), writes
a self-contained HTML page with the state embedded as `window.__STATE__`,
prints the path, and exits without serving. The same rendering is available
live at `/snapshot`. Snapshot pages do not poll; the ticker shows
`[SNAPSHOT]`.
