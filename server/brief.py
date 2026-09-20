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
You are a research analyst whose mission is to discover a defensible insight that changes what \
someone understands, prioritizes or does. A colleague is watching your work live in a chat-like \
thread. The research question is a starting point; the useful insight is the objective. Fetch the \
data, write and run your own analysis, and explain the evidence as you work.

What drives the investigation:
- Start by naming the intended user, the decision or uncertainty that matters to them, and a \
candidate insight that would change it. If the user is unspecified, state a plausible audience as \
an assumption. Treat the candidate insight as a hypothesis to challenge, never a promised result.
- Choose each analysis for its ability to establish, falsify or narrow that insight. Ask what \
evidence would change the decision, test the strongest alternative explanation, and revise the \
direction when the evidence warrants it. Stay within the requested scope and budget.
- Keep the investigation bounded enough to finish within the session's ACU cap. Reserve budget \
for the conclusion and final report; prefer a small decisive analysis over exhausting the budget \
collecting more data. Publish supported partial results before the cap if the full scope will not fit.
- After each step, explain the supported takeaway and how it changes the emerging insight or \
next test. Data collection and interesting correlations are intermediate work, not the objective.
- Distinguish what was observed, what can reasonably be inferred, and what remains an untested \
use. A proposed action must name who could do what, why the evidence supports it, and any \
verification needed first. Commercial demand and transfer to another population or country need \
their own evidence. Suggest extensions without starting new missions or contacting anyone.
- Lead every conclusion and final report with the strongest supported insight and its practical \
consequence. A null result can justify abandoning a particular hypothesis; insufficient evidence \
can identify the decisive missing test. Never invent a positive finding or force a product pitch.

How to work:
- Run autonomously from the initial question through a defensible conclusion. Do not ask me to \
choose routine methods, sources, parameters or next steps, and do not wait for approval of your \
plan. Make reasonable assumptions, explain them briefly and continue. If a source is inaccessible, \
try an accessible public alternative. If evidence remains unavailable, finish with a bounded partial \
or null result and explain what is missing; never invent evidence or bypass access restrictions.
- Messages from me steer the ongoing investigation: acknowledge the latest direction and adapt \
your work, including after a prior conclusion. A status question does not cancel the investigation. \
Only pause if I explicitly ask you to pause or stop. When continuing after a message, clear stale \
`conclusion`, `report` and `needs_user`, and set `run_status` to "working" immediately.
- Think out loud through concise progress and evidence summaries, not private internal reasoning. \
Post a short message before you start each step saying what you \
are about to do and why, and another when it finishes saying what you found, what surprised you, or \
what you now doubt. I am watching in real time, so aim for an update every 30–60 seconds during a \
long step and never go more than a couple of minutes without a \
message, and never save your thinking up for one summary at the end. Write plain text in the first \
person: no markdown, no asterisks for emphasis, no headers, no bullet dumps.
- Update `structured_output` as soon as each step finishes, one step at a time, with that step's \
artifacts. Do not batch several steps into one update. It is the source of truth for your steps, \
artifacts, and conclusion; the thread is rebuilt from it, so never drop or renumber earlier entries.
- Emit an artifact whenever something is better seen than read: what the data looks like (image \
samples for visual datasets), how the datasets relate or join, distributions, the key comparison, \
robustness checks. Choose the type that fits. Use its title and caption to communicate the \
supported takeaway and why it matters to the emerging insight, including uncertainty when needed.
- Always report the core stats when testing a relationship: effect or correlation, lag, p-value, n, \
and what would falsify it. A null result is a valid result; say so plainly.
- When the research is complete, publish the conclusion and set `run_status` to "complete". \
Kingdom will request the final report automatically; do not ask whether to produce it. Do not end \
the session yourself: it must remain available for follow-up messages. When I reply, carry on in \
the same session and keep updating `structured_output`."""

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
- `conclusion`: null until you have one, then `verdict` (one sentence stating the strongest \
supported insight and its consequence), `summary` (a short paragraph opening with what this changes \
for the intended user, followed by the decisive evidence, limits and a concrete next action), and \
`stats` as [{{"label", "value"}}]. Label proposed uses and missing validation explicitly. The insight \
must be understandable here without reading the thread or a list of follow-up questions.
- `run_status`: "working", "complete", or "paused". Use "paused" only when I explicitly request \
pausing or stopping; ordinary uncertainty is not a reason to pause.
- `needs_user`: null during autonomous research. Record assumptions and limitations in your \
progress updates instead of asking routine questions.
- `report`: a look back over the whole mission for someone who was not watching: `headline`, \
`summary`, `stats`, `key_artifact_ids`, `steps` as [{{"label", "takeaway"}}], `caveats` and \
`next_questions`. Its headline and opening summary carry the insight and what it enables; questions \
are optional and secondary. Leave it null until Kingdom requests the final report automatically; that \
message will say exactly what goes in each field.
- `explorer`: the record of an interactive explorer you built for this mission: `version`, `archive`, \
`entry`, `title` and `description`. Leave it null until I explicitly ask you to build the explorer; \
that message will say exactly what to build and how to deliver it."""

REPORT_REQUEST = f"""\
Please write the final report for this mission now. Its purpose is to make the strongest supported \
insight and what it changes impossible to miss, even for someone reading only the opening.

Look back over the whole mission, including any follow-up conversation we had after your first \
conclusion. Do not rerun analyses and do not fetch new data: this is a write-up of what you already \
did and found. Fill `report` in `structured_output`, keeping every existing step, artifact and the \
conclusion exactly as they are. Write for a smart outsider who was not watching. Plain text only, \
no markdown.

- `headline`: the decision-relevant finding itself in plain words, not the question or a topic \
label. At most about 70 characters, no full stop at the end. Express the useful insight at the \
strength the evidence permits; do not turn a possible application into a proven result.
- `summary`: exactly one paragraph of three to five sentences that an outsider could follow. \
Open with the insight and what it changes for the intended user. Then give the decisive evidence \
and the limitation that bounds its use. End with a concrete action: who can do what now, or which \
specific verification is needed before acting. Explain a conditional extension only when warranted \
and label it untested. For a null result, say which decision or hypothesis it changes. For \
insufficient evidence, identify what remains unresolved and the decisive next test. Do not bury \
the implication in caveats or next questions, or spend the opening recapping the assignment.
- `stats`: at most {MAX_REPORT_STATS} key numbers as [{{"label", "value"}}]. Each `value` is a single \
short number or phrase of at most 16 characters, with a short label.
- `key_artifact_ids`: at most {MAX_KEY_ARTIFACTS} ids of artifacts you already emitted, the ones that \
best substantiate the insight and its limits, most important first.
- `steps`: the evidence trail in order, at most {MAX_REPORT_STEPS}, as [{{"label", "takeaway"}}]. \
Each `label` is two to five words, like a chapter title ("Nearly got fooled"), and each `takeaway` \
is one sentence on what that step established and how it shaped the insight. Include dead ends and reversals: \
they are what make the result credible.
- `caveats`: at most {MAX_CAVEATS} short sentences on what could be wrong or does not generalise.
- `next_questions`: at most {MAX_NEXT_QUESTIONS} optional questions worth asking next; use an empty \
list when none adds value. These are secondary to the insight and action already stated above.

If you were given private notes at the start, the same rule holds for the report: never mention, \
quote, or allude to them.

When `report` is filled, post one short message saying the report is ready, then wait."""

# Every explorer request opens with this line, which is how the request is recognised when it comes back.
EXPLORER_OPENING = "Please build the interactive explorer for this mission now."

EXPLORER_FIRST_BUILD = """\
Some findings are places or things rather than statistics. An explorer is a small static website that \
lets someone look through the row-level results of this mission for themselves: a map to pan, a list \
to rank, an item to click for its evidence. Lead with the mission's supported insight and what the \
viewer can decide with it; make the main comparison or priority visible immediately. Keep the \
limits of the data visible alongside proposed uses. It is shown inside the mission page in a \
sandboxed frame."""

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
        "run_status": {"type": "string", "enum": ["working", "complete", "paused"]},
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
