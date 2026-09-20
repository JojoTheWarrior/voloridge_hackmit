# Round 2 mission-agent protocol

You are a **mission child** of the WarSignal MISSIONS BRAIN. You receive one
Round 2 hypothesis and a mission id (`R2-00NN`). GitHub `main` is the source of
truth: everything you produce is pushed there; nothing is returned only in chat.

Read: `AGENT.md`, `missions/ROUND2_RUBRIC.md`, `missions/status/SCHEMA.md`.

## 0. Setup (≤ 3 min)

```bash
git clone https://github.com/JojoTheWarrior/voloridge_hackmit.git && cd voloridge_hackmit
pip install -r requirements.txt
python main.py indicators | head        # registry sanity check
```

API keys (`OPENAI_API_KEY`, `DEVIN_API_KEY`, `TYPESAFE_API_KEY`) are **optional**.
If they are missing from your environment do **not** ask the user — ask your parent
(the brain session) once, then proceed with `--brain heuristic`. Never write a key
into a file that is committed. Never create or commit `.env`.

## 1. Announce

```bash
python main.py status R2-00NN --hypothesis "<full R2 line>" --title "<short title>" \
  --parent <parent id or omit> --session-url <your session url> --state running --stage planning --push
```

## 2. Heartbeat (every ≤ 3 min while working)

Run in the background for the duration of your work:

```bash
while true; do sleep 170; python main.py status R2-00NN --message "heartbeat" --push >/dev/null 2>&1; done &
```

## 3. Run the mission (writes stage updates for you)

```bash
python main.py mission "<full R2 line>" --mission-id R2-00NN --status --viz --publish --brain heuristic
```

`--status` makes the runner update `missions/status/R2-00NN.json` at planning →
loading → stats → judging → narrative → viz → trade → publishing, copies scores and
the `trade_idea` into it, and `--publish` commits **only** the run folder,
`missions/runs/INDEX.md` and your status file, then pulls `--rebase --autostash`
and pushes. The trade rule (`trade.json`, "Trade idea" section in `note.md`) is
computed automatically per `ROUND2_RUBRIC.md`.

If the command fails (e.g. `insufficient overlap`), you may fix the hypothesis
**once** (swap to a registered indicator with the same meaning) and rerun; otherwise
go to step 6 with `--state failed`.

## 4. Read the result

`missions/runs/<folder>/manifest.json` → `scores`, `actionability`, `trade_idea`;
`trade.json` → full metrics; `note.md` → narrative.

## 5. One follow-up hypothesis

Write exactly **one** new `R2 |` line that builds on what you learned (a different
target in the same channel, a tighter threshold, a reversal, a different lag, or a
null control if your result looks too good). It must use registered indicator names
and end with `[signal -> target]`. Then:

```bash
python main.py status R2-00NN --stage followup --followup "R2 | [channel] <text> [a -> b]" --push
```

This appends to `missions/queue.txt` atomically with ` (parent: R2-00NN)` and pushes.

## 6. Finish

```bash
python main.py status R2-00NN --state done --stage done --message "<one-line verdict>" --push
# or
python main.py status R2-00NN --state failed --message "<error>" --push
```

Return structured output:

```json
{"mission_id": "R2-00NN", "run_folder": "missions/runs/...", "scores": {...},
 "trade_idea": {...}, "followup_hypothesis": "R2 | ...", "status_url":
 "https://github.com/JojoTheWarrior/voloridge_hackmit/blob/main/missions/status/R2-00NN.json"}
```

## Hard rules

* Commit only `missions/status/R2-00NN.json`, your run folder, `missions/runs/INDEX.md`,
  and (for the follow-up) `missions/queue.txt`. Never edit another mission's files,
  never delete Round 1 folders, never force-push, never commit secrets or
  `missions/results.csv`.
* Push conflicts: `git pull --rebase --autostash` then push again (the CLI does this;
  retry up to 3 times, then report to your parent).
* Time cap **25 minutes** wall clock. At 22 minutes stop whatever you are doing and go
  to step 6 with `failed` if you have no run folder yet.
* Do not run other queue lines; the brain schedules them. The round terminates at
  200 Round 2 missions total.
* Report only what the data shows; correlation is not causation.

## Brain control protocol (pause / resume)

The MISSIONS BRAIN re-reads `missions/config.json` on every scheduling loop (~60 s):

* `max_agents == 0` → **PAUSE**: nothing new is spawned, in-flight children finish
  normally (they are never killed by a pause), the brain keeps polling the config and
  resumes automatically when `max_agents > 0`.
* A user or parent message saying `pause` pauses the same way; `resume` resumes
  (the brain also honours `/home/ubuntu/r2_pause` as a local pause flag).
* The brain never finishes its session while `missions/queue.txt` still has `R2 |`
  lines or any child is running; it only stops at the 200-mission cap or an empty,
  settled tree.
