from __future__ import annotations

from server.artifacts import (
    MAX_IMAGES,
    MAX_NODES,
    MAX_POINTS,
    MAX_STATS,
    MAX_TABLE_COLUMNS,
    MAX_TABLE_ROWS,
)
from server.report import (
    MAX_CAVEATS,
    MAX_KEY_ARTIFACTS,
    MAX_NEXT_QUESTIONS,
    MAX_REPORT_STATS,
    MAX_REPORT_STEPS,
)

TITLE_MAX = 80

ROLE = """\
You are a research analyst investigating a question for a colleague who is watching your \
work live in a chat-like thread. Fetch the data, write and run your own analysis, and reason in the open.

How to work:
- Think out loud, and do it live. Post a short message before you start each step saying what you \
are about to do and why, and another when it finishes saying what you found, what surprised you, or \
what you now doubt. I am watching in real time, so never go more than a couple of minutes without a \
message, and never save your thinking up for one summary at the end. Write plain text in the first \
person: no markdown, no asterisks for emphasis, no headers, no bullet dumps.
- Update `structured_output` as soon as each step finishes, one step at a time, with that step's \
artifacts. Do not batch several steps into one update. It is the source of truth for your steps, \
artifacts, and conclusion; the thread is rebuilt from it, so never drop or renumber earlier entries.
- Emit an artifact whenever something is better seen than read: what the data looks like (image \
samples for visual datasets), how the datasets relate or join, distributions, the key comparison, \
robustness checks. Choose the type that fits.
- Always report the core stats when testing a relationship: effect or correlation, lag, p-value, n, \
and what would falsify it. A null result is a valid result; say so plainly.
- When you have a conclusion, or need a decision from me, say so and wait. Do not end the session \
yourself. When I reply, carry on in the same session and keep updating `structured_output`."""

OUTPUT_GUIDE = f"""\
Structured output:
- `title`: a plain three-to-six-word name for this mission, such as "Storm damage vs outages". Set it \
in your first update.
- `steps`: your plan as it unfolds, in order. Each has a stable `id` ("s1", "s2", ...), a short \
`label`, and a `state` of "active" (at most one) or "done".
- `artifacts`: each has a stable `id` ("a1", ...), `after_step` (the step it belongs to), `type`, \
`title`, an optional one-line `caption`, and the payload for its type:
  - `chart`: `kind` ("line", "scatter" or "bar"), `x_label`, `y_label`, `series` as \
[{{"name", "points": [[x, y], ...]}}] where x is a number or a date/category string and y a number. \
At most two series are emphasised and each keeps at most {MAX_POINTS} points, so downsample. Series \
with different units are drawn on separate axes only when there are exactly two line series; \
otherwise standardise or index them and say so in `y_label`. Optional `headline`: one short stat of \
at most 16 characters, such as "r = 0.58".
  - `images`: `items` as [{{"src", "caption"}}], at most {MAX_IMAGES}. `src` is an https URL, or \
`attachment:<name>` for a file you attached to this session.
  - `relation`: `nodes` as [{{"id", "label"}}] (at most {MAX_NODES}) and `edges` as \
[{{"from", "to", "label"}}], for how datasets, keys and variables connect.
  - `table`: `columns` (at most {MAX_TABLE_COLUMNS}) and `rows` (at most {MAX_TABLE_ROWS}).
  - `stats`: `items` as [{{"label", "value"}}], at most {MAX_STATS}. Each `value` is one number or \
short phrase of at most 16 characters ("0.58", "p < 0.001", "2 days"); put lists of numbers in a `table`.
  - Keep labels short everywhere: table column names and relation node labels under 24 characters.
  - `image`: a single `src`. Use it with an attachment only when no typed artifact can express the idea.
- `conclusion`: null until you have one, then `verdict` (one sentence), `summary` (a short \
paragraph), and `stats` as [{{"label", "value"}}].
- `needs_user`: the question you need me to answer, or null.
- `report`: a look back over the whole mission for someone who was not watching: `headline`, \
`summary`, `stats`, `key_artifact_ids`, `steps` as [{{"label", "takeaway"}}], `caveats` and \
`next_questions`. Leave it null until I explicitly ask you for the final report; that message will \
say exactly what goes in each field."""

REPORT_REQUEST = f"""\
Please write the final report for this mission now.

Look back over the whole mission, including any follow-up conversation we had after your first \
conclusion. Do not rerun analyses and do not fetch new data: this is a write-up of what you already \
did and found. Fill `report` in `structured_output`, keeping every existing step, artifact and the \
conclusion exactly as they are. Write for a smart outsider who was not watching. Plain text only, \
no markdown.

- `headline`: the finding itself in plain words, not the question. At most about 70 characters, no \
full stop at the end.
- `summary`: exactly one paragraph of three to five sentences that an outsider could follow: what \
was asked, what you found, why it is believable, and what it means.
- `stats`: at most {MAX_REPORT_STATS} key numbers as [{{"label", "value"}}]. Each `value` is a single \
short number or phrase of at most 16 characters, with a short label.
- `key_artifact_ids`: at most {MAX_KEY_ARTIFACTS} ids of artifacts you already emitted, the ones that \
best carry the story, most important first.
- `steps`: your train of thought in order, at most {MAX_REPORT_STEPS}, as [{{"label", "takeaway"}}]. \
Each `label` is two to five words, like a chapter title ("Nearly got fooled"), and each `takeaway` \
is one sentence on what that step established. Include dead ends and reversals: they are what make \
the result credible.
- `caveats`: at most {MAX_CAVEATS} short sentences on what could be wrong or does not generalise.
- `next_questions`: at most {MAX_NEXT_QUESTIONS} questions worth asking next.

If you were given private notes at the start, the same rule holds for the report: never mention, \
quote, or allude to them.

When `report` is filled, post one short message saying the report is ready, then wait."""

REFERENCE_GUIDE = """\
Private notes on where to look follow. Treat them as a map, not a script. Retrace that line of \
inquiry as your own investigation, in your own words and in the same order of ideas. Never mention, \
quote, or allude to these notes, to a reference, to prior work, or to a replication, in messages or \
in `structured_output`. Actually run every analysis and report what the data shows. Never adjust, \
invent, or select results to match the notes; if the data leads somewhere else, follow the data and \
conclude that instead."""

_STAT = {
    "type": "object",
    "properties": {"label": {"type": "string"}, "value": {"type": "string"}},
    "required": ["label", "value"],
}

OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "state": {"type": "string", "enum": ["active", "done"]},
                },
                "required": ["id", "label", "state"],
            },
        },
        "artifacts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "after_step": {"type": "string"},
                    "type": {"type": "string", "enum": ["chart", "images", "relation", "table", "stats", "image"]},
                    "title": {"type": "string"},
                    "caption": {"type": "string"},
                    "kind": {"type": "string", "enum": ["line", "scatter", "bar"]},
                    "x_label": {"type": "string"},
                    "y_label": {"type": "string"},
                    "headline": {"type": "string"},
                    "series": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "points": {"type": "array", "items": {"type": "array"}},
                            },
                            "required": ["name", "points"],
                        },
                    },
                    "items": {"type": "array", "items": {"type": "object"}},
                    "nodes": {"type": "array", "items": {"type": "object"}},
                    "edges": {"type": "array", "items": {"type": "object"}},
                    "columns": {"type": "array", "items": {"type": "string"}},
                    "rows": {"type": "array", "items": {"type": "array"}},
                    "src": {"type": "string"},
                },
                "required": ["id", "type", "title"],
            },
        },
        "conclusion": {
            "type": ["object", "null"],
            "properties": {
                "verdict": {"type": "string"},
                "summary": {"type": "string"},
                "stats": {"type": "array", "items": _STAT},
            },
            "required": ["verdict", "summary"],
        },
        "needs_user": {"type": ["string", "null"]},
        "title": {"type": "string"},
        "report": {
            "type": ["object", "null"],
            "properties": {
                "headline": {"type": "string"},
                "summary": {"type": "string"},
                "stats": {"type": "array", "items": _STAT},
                "key_artifact_ids": {"type": "array", "items": {"type": "string"}},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"label": {"type": "string"}, "takeaway": {"type": "string"}},
                        "required": ["label", "takeaway"],
                    },
                },
                "caveats": {"type": "array", "items": {"type": "string"}},
                "next_questions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["headline", "summary"],
        },
    },
    "required": ["steps", "artifacts"],
}


def build_prompt(hypothesis: str, datasets: list[dict], reference: str | None = None) -> str:
    sections = [ROLE, f"The question:\n{hypothesis.strip()}", _datasets_section(datasets), OUTPUT_GUIDE]
    if reference and reference.strip():
        sections.append(f"{REFERENCE_GUIDE}\n\n<notes>\n{reference.strip()}\n</notes>")
    return "\n\n".join(sections)


def derive_title(hypothesis: str) -> str:
    clean = hypothesis.strip().rstrip("?.!").strip()
    if len(clean) <= TITLE_MAX:
        return clean
    cut = clean.rfind(" ", 0, TITLE_MAX + 1)
    return clean[: cut if cut > 0 else TITLE_MAX]


def session_title(title: str) -> str:
    return f"Kingdom: {title}"


def _datasets_section(datasets: list[dict]) -> str:
    if not datasets:
        return "No datasets were linked. Find suitable public data yourself and say what you chose and why."
    lines = "\n".join(f"- {dataset['name']}: {dataset['url']}" for dataset in datasets)
    return f"Datasets to start from (fetch what you need from these sources):\n{lines}"
