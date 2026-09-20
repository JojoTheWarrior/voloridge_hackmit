# Mission progress schema (missions/status/)

Every running mission agent writes `missions/status/<mission_id>.json` and pushes it to
GitHub (`main`) every time it reaches a new stage and at least every 3 minutes while
working. When the mission finishes, `state` becomes `done` or `failed` and the file is
pushed one last time together with the run folder `missions/runs/<folder>/`.
GitHub is the source of truth: UIs (`python main.py kingdom`, the Kingdom Terminal web UI)
`git pull` (or fetch raw files) and read this directory. Finished files older than 7 days
may be moved to `missions/status/archive/`.

```json
{
  "schema_version": 1,
  "mission_id": "R2-0042",
  "title": "Hormuz news share leads Brent–WTI spread",
  "hypothesis": "GDELT Hormuz mention share leads the Brent–WTI spread by 1-3 days.",
  "parent_mission_id": "R2-0017",
  "round": "iran-round-2",
  "agent_session_url": "https://app.devin.ai/sessions/<id>",
  "brain_sessions": [{"purpose": "planner", "session_url": "https://app.devin.ai/sessions/<id>"}],
  "state": "running",
  "stage": "stats",
  "progress": 0.55,
  "signal": 0.3,
  "started_at": "2026-09-21T03:10:00Z",
  "updated_at": "2026-09-21T03:16:30Z",
  "finished_at": null,
  "elapsed_s": 390,
  "message": "Permutation test running (n=140, max lag 5d).",
  "run_folder": "missions/runs/20260921-131-gdelt-gkg-hormuz-share_x_finance-spread-brent-wti",
  "scores": {"validity": null, "interestingness": null, "unexpectedness": null, "actionability": null},
  "trade_idea": null,
  "followup_hypothesis": null
}
```

Field rules:

- `state`: `queued` | `running` | `done` | `failed`.
- `stage` (ordered): `queued`, `planning`, `loading`, `stats`, `judging`, `narrative`, `viz`, `trade`, `followup`, `publishing`, `done`.
- `progress`: 0.0–1.0, monotone non-decreasing; roughly stage index / 10.
- `signal`: 0.0 (noise) – 1.0 (signal); null until judged. Drives red→green progress bar colour.
  Recommended: `signal = validity/10` once Jev scores exist, else `1 - perm_p` clipped to [0,1].
- `scores`: Jev 0–10 scores; `actionability` is the Round-2 trade rubric (0–10).
- `trade_idea` (when done): `{"instrument": "BZ=F", "direction": "long", "entry_rule": "...",
  "exit_rule": "...", "holding_days": 3, "hit_rate": 0.61, "avg_return": 0.012, "n_trades": 28,
  "sharpe_like": 0.9, "caveats": "..."}` — a rule that could be re-run on new data, not a story.
- `followup_hypothesis`: the one new hypothesis this mission appends to `missions/queue.txt`.
- Timestamps are UTC ISO-8601; `elapsed_s` = `updated_at - started_at`.
- Writers must write atomically (temp file + rename) and never edit another mission's file.
- Concurrency cap lives in `missions/config.json` → `{"max_agents": 5}`; the orchestrator reads it on every scheduling loop so it can be changed without a restart.
