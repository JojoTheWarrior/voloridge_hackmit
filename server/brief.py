from __future__ import annotations

import re

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
KIT_GUIDE = "GUIDE.md"
# The worked example's data only shows a shape, and Devin must not reuse it, so a long file is cut short.
KIT_DATA_SUFFIXES = (".json", ".geojson", ".csv")
MAX_KIT_DATA_CHARS = 20_000

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
say exactly what goes in each field.
- `explorer`: the record of an interactive explorer you built for this mission: `version`, `archive`, \
`entry`, `title` and `description`. Leave it null until I explicitly ask you to build the explorer; \
that message will say exactly what to build and how to deliver it."""

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

# Every explorer request opens with this line, which is how the request is recognised when it comes back.
EXPLORER_OPENING = "Please build the interactive explorer for this mission now."

EXPLORER_FIRST_BUILD = """\
Some findings are places or things rather than statistics. An explorer is a small static website that \
lets someone look through the row-level results of this mission for themselves: a map to pan, a list \
to rank, an item to click for its evidence. It is shown inside the mission page in a sandboxed frame."""

EXPLORER_CHANGE = """\
This is a change request. If you have already built an explorer in this session, apply the \
instructions below to it and deliver the result as the next version; if you have not, build the \
first one with them in mind.

<instructions>
{instructions}
</instructions>"""

EXPLORER_KIT_INTRO = """\
What keeps an explorer looking like the rest of the app is the explorer kit: a stylesheet, optional \
helpers, one complete worked example, and a guide. Read the guide first. It and every kit file follow \
in full, each under the path it has inside a site. The kit is a design system and a starting point, \
not a widget: restructure or replace the example freely, but keep to the guide."""

EXPLORER_DELIVERY = """\
How to build and deliver it:
- Build a static site whose entry document is `index.html`, with every path in it relative.
- Reference the kit only by the relative paths `kit/kit.css` and `kit/kit.js`. Those two are served \
by the app, which always supplies its own current copy; put a copy of the kit in your site only so \
that you can test it locally.
- The site loads its own data from relative files next to it, such as `data.json`. That data must be \
real row-level results you already computed in this session. Never invent data, never ship sample or \
placeholder data, and do not leave the worked example's data in place. If this mission has no \
place-level or item-level data worth exploring, say so in a message and do not deliver an explorer.
- Allowed file types: html, css, js, mjs, json, geojson, csv, txt, png, jpg, jpeg, webp, gif, svg, \
woff2. At most 200 files, 25 MB per file and 40 MB in total, with no symlinks.
- Test it in your own browser before delivering: in both themes (open it with `?theme=dark` and with \
`?theme=light`) and at a narrow phone width. Fix what looks broken.
- Zip the site root as `explorer-v<N>.zip`, where N is one higher than your previous build in this \
session, starting at 1. {numbering}Attach that one archive to this session.
- Then set `explorer` in `structured_output` to {{"version": N, "archive": "explorer-v<N>.zip", \
"entry": "index.html", "title", "description"}}, keeping every existing step, artifact, the conclusion \
and any report exactly as they are. `title` is a plain three-to-six-word name for the explorer; \
`description` is one or two sentences on what can be explored and how.
- If you were given private notes at the start, the same rule holds for the explorer and everything \
in it: never mention, quote, or allude to them.

When `explorer` is set, post one short message saying the explorer is ready, then wait."""

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
        "explorer": {
            "type": ["object", "null"],
            "properties": {
                "version": {"type": "integer"},
                "archive": {"type": "string"},
                "entry": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["version", "archive", "entry", "title", "description"],
        },
    },
    "required": ["steps", "artifacts"],
}


def build_prompt(hypothesis: str, datasets: list[dict], reference: str | None = None) -> str:
    sections = [ROLE, f"The question:\n{hypothesis.strip()}", _datasets_section(datasets), OUTPUT_GUIDE]
    if reference and reference.strip():
        sections.append(f"{REFERENCE_GUIDE}\n\n<notes>\n{reference.strip()}\n</notes>")
    return "\n\n".join(sections)


def build_explorer_request(
    instructions: str | None, kit: dict[str, str], *, next_version: int | None = None
) -> str:
    """The message that asks Devin for an explorer build. `kit` maps each kit file's path inside a
    site to its text, with the guide under `GUIDE.md`. With `instructions` it is a change request."""
    instructions = (instructions or "").strip()
    sections = [EXPLORER_OPENING, EXPLORER_CHANGE.format(instructions=instructions) if instructions
                else EXPLORER_FIRST_BUILD]
    guide = kit.get(KIT_GUIDE, "").strip()
    files = [(path, text) for path, text in kit.items() if path != KIT_GUIDE]
    if guide or files:
        sections.append(EXPLORER_KIT_INTRO)
    if guide:
        sections.append(_kit_block(KIT_GUIDE, guide))
    sections.extend(_kit_block(path, text) for path, text in files)
    numbering = ""
    if next_version:
        numbering = f"This build is number {next_version}, so name it `explorer-v{next_version}.zip`. "
    sections.append(EXPLORER_DELIVERY.format(numbering=numbering))
    return "\n\n".join(sections)


def is_explorer_request(text: str) -> bool:
    return " ".join(text.split()).startswith(EXPLORER_OPENING)


def read_explorer_request(text: str) -> tuple[str | None, int | None]:
    """The instructions and build number inside a request made by `build_explorer_request`."""
    # The kit is quoted in full and may say anything, so it is set aside first.
    text = re.sub(r"<kit-file path=\"[^\"]*\">\n.*?\n</kit-file>", "", text, flags=re.DOTALL)
    instructions = re.search(r"<instructions>\n(.*?)\n</instructions>", text, re.DOTALL)
    number = re.search(r"This build is number (\d+),", text)
    return (instructions.group(1) if instructions else None), (int(number.group(1)) if number else None)


def _kit_block(path: str, text: str) -> str:
    text = text.rstrip()
    if path.endswith(KIT_DATA_SUFFIXES) and len(text) > MAX_KIT_DATA_CHARS:
        left_out = len(text) - MAX_KIT_DATA_CHARS
        note = f"[the example's data goes on in the same shape; {left_out} more characters left out]"
        text = f"{text[:MAX_KIT_DATA_CHARS]}\n{note}"
    return f"<kit-file path=\"{path}\">\n{text}\n</kit-file>"


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
