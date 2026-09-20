from __future__ import annotations

import copy
import re
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import quote, urlsplit

import requests

from server.brief import REPORT_REQUEST
from warsignal.config import env

DEFAULT_MAX_ACU = 5
DEFAULT_MODE = "fast"
DEVIN_MODES = ("normal", "fast", "lite", "ultra", "fusion")
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
RETRY_STATUSES = {429, 500, 502, 503, 504}
MESSAGE_PAGE_SIZE = 200
MAX_MESSAGE_PAGES = 25

# v3 session state -> the four states the rest of the server understands.
# `status` alone decides unless `status_detail` is listed too, in which case the detail wins
# (a `running` session that is `waiting_for_user` is waiting). A `status` of error always wins.
# Anything unlisted counts as running, so a new Devin state never fails a mission by surprise.
# Values are from the v3 docs; correct them here after a live smoke test.
STATUS_MAP = {
    "new": "running",
    "claimed": "running",
    "running": "running",
    "resuming": "running",
    "suspended": "waiting",
    "exit": "finished",
    "error": "error",
}
STATUS_DETAIL_MAP = {
    "working": "running",
    "waiting_for_user": "waiting",
    "waiting_for_approval": "waiting",
    "finished": "finished",
    "inactivity": "waiting",
    "user_request": "waiting",
    "usage_limit_exceeded": "error",
    "out_of_credits": "error",
    "out_of_quota": "error",
    "no_quota_allocation": "error",
    "payment_declined": "error",
    "org_usage_limit_exceeded": "error",
    "user_usage_limit_exceeded": "error",
    "total_session_limit_exceeded": "error",
    "error": "error",
}

# Message fields that may say who wrote it, most trusted first, and the values that mean "the user".
# Anything unrecognised counts as Devin: showing an echo is a smaller failure than hiding Devin's work.
ROLE_FIELDS = ("source", "role", "sender", "author", "type")
USER_MARKERS = ("user", "human")
DEVIN_MARKERS = ("devin", "assistant", "agent")


@dataclass(frozen=True)
class SessionRef:
    session_id: str
    url: str | None


@dataclass(frozen=True)
class DevinMessage:
    id: str
    role: str  # "devin" | "user"
    text: str
    at: str  # ISO 8601 UTC, or "" when Devin gave no usable timestamp


@dataclass(frozen=True)
class Attachment:
    name: str
    url: str


@dataclass(frozen=True)
class SessionSnapshot:
    status: str  # "running" | "waiting" | "finished" | "error"
    detail: str | None
    structured_output: dict | None


class DevinUnavailable(RuntimeError):
    pass


class AttachmentRejected(RuntimeError):
    pass


class DevinClient(Protocol):
    def create_session(self, prompt: str, *, title: str, schema: dict, max_acu: int) -> SessionRef: ...
    def get_session(self, session_id: str) -> SessionSnapshot: ...
    def list_messages(self, session_id: str) -> list[DevinMessage]: ...
    def send_message(self, session_id: str, text: str) -> None: ...
    def list_attachments(self, session_id: str) -> list[Attachment]: ...
    def download(self, attachment: Attachment) -> tuple[bytes, str]: ...


def make_client() -> tuple[DevinClient, bool]:
    """The client to use and whether it is the scripted demo."""
    api_key = env("DEVIN_API_KEY").strip()
    if not api_key or env("KINGDOM_FAKE_DEVIN") == "1":
        return FakeDevin(), True
    return V3DevinClient(api_key, mode=devin_mode()), False


def devin_mode() -> str:
    mode = env("KINGDOM_DEVIN_MODE", DEFAULT_MODE).strip().lower()
    return mode if mode in DEVIN_MODES else DEFAULT_MODE


def max_acu() -> int:
    try:
        value = int(env("KINGDOM_MAX_ACU", str(DEFAULT_MAX_ACU)))
    except ValueError:
        return DEFAULT_MAX_ACU
    return value if value > 0 else DEFAULT_MAX_ACU


def normalise_status(status: object, detail: object) -> str:
    status = status.lower() if isinstance(status, str) else ""
    detail = detail.lower() if isinstance(detail, str) else ""
    if STATUS_MAP.get(status) == "error":
        return "error"
    return STATUS_DETAIL_MAP.get(detail) or STATUS_MAP.get(status, "running")


class V3DevinClient:
    base_url = "https://api.devin.ai"

    def __init__(self, api_key: str, *, mode: str = DEFAULT_MODE, sleep: Callable[[float], None] = time.sleep):
        self._api_key = api_key
        self.mode = mode
        self._sleep = sleep
        self._org_id: str | None = None
        self._org_lock = threading.Lock()

    def __repr__(self) -> str:
        return f"V3DevinClient(mode={self.mode!r})"

    def create_session(self, prompt: str, *, title: str, schema: dict, max_acu: int) -> SessionRef:
        body = {
            "prompt": prompt,
            "title": title,
            "max_acu_limit": max_acu,
            "devin_mode": self.mode,
            "structured_output_schema": schema,
        }
        created = self._call("POST", self._sessions(), "session creation", json=body)
        session_id = created.get("session_id") if isinstance(created, dict) else None
        if not isinstance(session_id, str) or not session_id:
            raise DevinUnavailable("invalid Devin session response: no session_id")
        url = created.get("url")
        return SessionRef(session_id, url if isinstance(url, str) and url else None)

    def get_session(self, session_id: str) -> SessionSnapshot:
        data = self._call("GET", self._sessions(session_id), "session status")
        if not isinstance(data, dict):
            raise DevinUnavailable("invalid Devin session response")
        detail = data.get("status_detail")
        output = data.get("structured_output")
        return SessionSnapshot(
            status=normalise_status(data.get("status"), detail),
            detail=detail if isinstance(detail, str) and detail else None,
            structured_output=output if isinstance(output, dict) else None,
        )

    def list_messages(self, session_id: str) -> list[DevinMessage]:
        items: list = []
        params: dict = {"first": MESSAGE_PAGE_SIZE}
        for _ in range(MAX_MESSAGE_PAGES):
            page = self._call("GET", self._sessions(session_id, "messages"), "message list", params=dict(params))
            items.extend(_items(page))
            cursor = page.get("end_cursor") if isinstance(page, dict) else None
            if not (isinstance(page, dict) and page.get("has_next_page") and cursor):
                break
            params["after"] = cursor
        messages = []
        for index, item in enumerate(items):
            if isinstance(item, dict) and (message := _message(index, item)):
                messages.append(message)
        return messages

    def send_message(self, session_id: str, text: str) -> None:
        self._call("POST", self._sessions(session_id, "messages"), "message", json={"message": text}, parse=False)

    def list_attachments(self, session_id: str) -> list[Attachment]:
        page = self._call("GET", self._sessions(session_id, "attachments"), "attachment list")
        attachments = []
        for item in _items(page):
            if not isinstance(item, dict):
                continue
            name, url = item.get("name"), item.get("url")
            if isinstance(name, str) and name and isinstance(url, str) and url:
                attachments.append(Attachment(name, url))
        return attachments

    def download(self, attachment: Attachment) -> tuple[bytes, str]:
        parts = urlsplit(attachment.url)
        if parts.scheme != "https" or not parts.hostname:
            raise AttachmentRejected("attachment URL is not https")
        # Attachment URLs are usually pre-signed storage links; the key only goes to Devin itself.
        host = parts.hostname.lower()
        headers = self._headers if host == "devin.ai" or host.endswith(".devin.ai") else {}
        try:
            response = requests.request("GET", attachment.url, headers=headers, stream=True, timeout=30)
        except requests.RequestException as exc:
            raise AttachmentRejected(f"attachment download failed: {exc}") from exc
        try:
            return _read_image(response)
        finally:
            response.close()

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _sessions(self, session_id: str | None = None, child: str | None = None) -> str:
        parts = [f"/v3/organizations/{quote(self._org(), safe='')}/sessions"]
        if session_id is not None:
            parts.append(quote(session_id, safe=""))
        if child is not None:
            parts.append(child)
        return "/".join(parts)

    def _org(self) -> str:
        with self._org_lock:
            if self._org_id is None:
                me = self._call("GET", "/v3/self", "identity lookup")
                org_id = me.get("org_id") if isinstance(me, dict) else None
                if not isinstance(org_id, str) or not org_id:
                    raise DevinUnavailable("Devin did not report an organization for this key")
                self._org_id = org_id
            return self._org_id

    def _call(self, method: str, path: str, what: str, *, parse: bool = True, **kwargs) -> object:
        response = None
        for attempt in range(2):
            try:
                response = requests.request(
                    method, f"{self.base_url}{path}", headers=self._headers, timeout=30, **kwargs
                )
            except requests.RequestException as exc:
                raise DevinUnavailable(f"Devin {what} failed: {exc}") from exc
            if response.status_code in RETRY_STATUSES and attempt == 0:
                self._sleep(1)
                continue
            break
        if response.status_code >= 400:
            detail = (getattr(response, "text", "") or "")[:300]
            raise DevinUnavailable(f"Devin {what} failed ({response.status_code}): {detail}")
        if not parse:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise DevinUnavailable(f"invalid Devin {what} response: {exc}") from exc


def _items(page: object) -> list:
    if isinstance(page, dict):
        page = page.get("items")
    return page if isinstance(page, list) else []


def _message(index: int, item: dict) -> DevinMessage | None:
    text = next((item[k] for k in ("message", "text", "content") if isinstance(item.get(k), str)), "").strip()
    if not text:
        return None
    at = next((stamp for k in ("created_at", "timestamp", "time") if (stamp := _iso(item.get(k)))), "")
    raw_id = next((item[k] for k in ("event_id", "message_id", "id") if item.get(k) not in (None, "")), None)
    # Without an id, position + time is the most stable handle on an append-only list.
    message_id = str(raw_id) if raw_id is not None else f"{index}:{at}"
    return DevinMessage(message_id, _role(item), text, at)


def _role(item: dict) -> str:
    for name in ROLE_FIELDS:
        value = item.get(name)
        if not isinstance(value, str):
            continue
        value = value.lower()
        if any(marker in value for marker in DEVIN_MARKERS):
            return "devin"
        if any(marker in value for marker in USER_MARKERS):
            return "user"
    return "devin"


def _iso(value: object) -> str:
    if isinstance(value, bool):
        return ""
    try:
        if isinstance(value, (int, float)):
            seconds = value / 1000 if value > 1e11 else value
            moment = datetime.fromtimestamp(seconds, timezone.utc)
        elif isinstance(value, str):
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
        else:
            return ""
    except (ValueError, OverflowError, OSError):
        return ""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_image(response) -> tuple[bytes, str]:
    if response.status_code >= 400:
        raise AttachmentRejected(f"attachment download failed ({response.status_code})")
    content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    # SVG can carry script, and this is served from the app's own origin.
    if not content_type.startswith("image/") or content_type == "image/svg+xml":
        raise AttachmentRejected(f"attachment is not an image ({content_type or 'unknown type'})")
    declared = response.headers.get("Content-Length")
    if declared and declared.isdigit() and int(declared) > MAX_ATTACHMENT_BYTES:
        raise AttachmentRejected("attachment is larger than 10 MB")
    data = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        data.extend(chunk)
        if len(data) > MAX_ATTACHMENT_BYTES:
            raise AttachmentRejected("attachment is larger than 10 MB")
    return bytes(data), content_type


# ---------- demo mode ----------

@dataclass(frozen=True)
class Beat:
    """One tick of the scripted run: what Devin says and how its structured output moves."""

    say: str | None = None
    start: tuple[str, str] | None = None  # (step id, label) becomes active; the previous step is done
    artifact: dict | None = None
    conclusion: dict | None = None


def _picsum(seed: str) -> str:
    return f"https://picsum.photos/seed/{seed}/640/420"


_SCATTER = [[round(0.04 + 0.03 * i, 2), round(2.1 + 0.34 * i + ((i * 7) % 5 - 2) * 0.9, 1)] for i in range(28)]
_WEEKLY = [[f"2026-{1 + i // 4:02d}-{1 + 7 * (i % 4):02d}", round(40 + 9 * ((i * 5) % 7) - i * 0.4, 1)] for i in range(24)]

SCRIPT: tuple[Beat, ...] = (
    Beat(say="I'll start by pulling both sources and looking at what is actually in them before testing anything.",
         start=("s1", "Read the datasets")),
    Beat(say="The first source is visual, so here is a sample of what the raw records look like. Quality is uneven: "
             "about one in ten is too cloudy to use.",
         artifact={"id": "a1", "after_step": "s1", "type": "images", "title": "Sample records",
                   "caption": "Eight records drawn at random",
                   "items": [{"src": _picsum(f"kingdom-{i}"), "caption": f"Record {i}"} for i in range(1, 9)]}),
    Beat(say="Neither source shares an id with the other, so I need a join. Both carry a region and a date, which "
             "is enough if I aggregate to region-weeks.",
         start=("s2", "Work out how they join"),
         artifact={"id": "a2", "after_step": "s2", "type": "relation", "title": "How the sources join",
                   "nodes": [{"id": "a", "label": "Source A records"}, {"id": "b", "label": "Source B series"},
                             {"id": "rw", "label": "Region-week panel"}, {"id": "y", "label": "Outcome"}],
                   "edges": [{"from": "a", "to": "rw", "label": "region + week"},
                             {"from": "b", "to": "rw", "label": "region + week"},
                             {"from": "rw", "to": "y", "label": "model"}]}),
    Beat(say="The join keeps 412 region-weeks out of 455. The ones that drop are all from the first month, "
             "before the second source starts reporting.",
         start=("s3", "Look at the distributions"),
         artifact={"id": "a3", "after_step": "s3", "type": "table", "title": "Panel coverage by region",
                   "columns": ["Region", "Weeks", "Mean A", "Mean B"],
                   "rows": [["North", "104", "0.31", "9.4"], ["South", "103", "0.22", "6.1"],
                            ["East", "104", "0.41", "12.8"], ["West", "101", "0.18", "5.0"]]}),
    Beat(say="Source B has a clear weekly rhythm and a slow downward drift, so I'll difference it before "
             "correlating; otherwise the trend alone would manufacture a relationship.",
         artifact={"id": "a4", "after_step": "s3", "type": "chart", "kind": "line", "title": "Source B over time",
                   "x_label": "Week", "y_label": "Level", "series": [{"name": "Source B", "points": _WEEKLY}]}),
    Beat(say="Now the actual test. I'm correlating A against B at lags from zero to four weeks and keeping the "
             "lag that fits best, with a permutation test so the choice of lag doesn't flatter the p-value.",
         start=("s4", "Test the relationship")),
    Beat(say="There is a relationship, and it is positive, but it is looser than I expected from the raw plots.",
         artifact={"id": "a5", "after_step": "s4", "type": "chart", "kind": "scatter",
                   "title": "A against B, one week later", "headline": "r = 0.58",
                   "x_label": "Source A share", "y_label": "Source B level",
                   "series": [{"name": "Region-weeks", "points": _SCATTER}]}),
    Beat(say="One thing bothered me: a single region supplies most of the extreme points. I reran everything "
             "without it to see whether the result survives.",
         start=("s5", "Check robustness"),
         artifact={"id": "a6", "after_step": "s5", "type": "stats", "title": "With and without the outlier region",
                   "items": [{"label": "r, all regions", "value": "0.58"}, {"label": "r, without East", "value": "0.49"},
                             {"label": "Best lag", "value": "1 week"}, {"label": "p-value", "value": "0.003"},
                             {"label": "n", "value": "412"}]}),
    Beat(say="It survives, a little weaker. I also mapped the residuals to check they aren't clustered in space.",
         artifact={"id": "a7", "after_step": "s5", "type": "image", "title": "Residual map",
                   "caption": "No obvious spatial clustering", "src": _picsum("kingdom-residuals")}),
    Beat(say="I have a conclusion. Tell me if you want me to push on anything, otherwise mark this done.",
         conclusion={"verdict": "A real but modest link: A leads B by about a week.",
                     "summary": "Across 412 region-weeks, A correlates with B one week later at r = 0.58 "
                                "(p = 0.003, permutation test over lags 0 to 4). Dropping the most extreme region "
                                "lowers it to 0.49 but does not remove it. A flat or negative correlation in a "
                                "fresh quarter of data would falsify this.",
                     "stats": [{"label": "Correlation", "value": "0.58"}, {"label": "Lag", "value": "1 week"},
                               {"label": "p-value", "value": "0.003"}, {"label": "n", "value": "412"}]}),
)

REPLY_ACK = "Good point. Let me rerun the comparison with that in mind."
REPLY_DONE = "Done. I split the panel in half by date and the link holds in both halves, so the conclusion stands."
REPORT_READY = "The report is ready."

REPORT = {
    "headline": "A leads B by about a week, but only modestly",
    "summary": "The question was whether movements in source A show up later in source B. Across 412 "
               "region-weeks they do: A correlates with B one week later at r = 0.58, and a permutation test "
               "over lags of zero to four weeks puts the p-value at 0.003. The link is believable because it "
               "was tested only after B's own downward drift was removed, and it survives dropping the one "
               "region that supplies most of the extreme points. It is a real but modest lead, useful as an "
               "early signal rather than a forecast.",
    "stats": [{"label": "Correlation", "value": "0.58"}, {"label": "Lead", "value": "1 week"},
              {"label": "p-value", "value": "0.003"}, {"label": "Region-weeks", "value": "412"}],
    "key_artifact_ids": ["a5", "a2", "a6"],
    "steps": [
        {"label": "Looked before testing",
         "takeaway": "A sample of the raw records showed about one in ten is too cloudy to use."},
        {"label": "Found the join",
         "takeaway": "With no shared id, both sources were aggregated to region-weeks, which kept 412 of 455."},
        {"label": "Nearly got fooled",
         "takeaway": "The raw series seemed to move together, but most of that was source B's own downward "
                     "drift, so it was differenced before any test."},
        {"label": "Tested the link",
         "takeaway": "A leads B by one week at r = 0.58, with a permutation test so that choosing the best "
                     "lag did not flatter the p-value."},
        {"label": "Doubted one region",
         "takeaway": "East supplies most of the extreme points, and dropping it lowers the correlation to "
                     "0.49 without removing it."},
        {"label": "Checked the map",
         "takeaway": "The residuals show no spatial clustering, so the link is not an artefact of "
                     "neighbouring regions."},
    ],
    "caveats": ["One region drives much of the strength, and without it the correlation falls to 0.49.",
                "The first month is missing because source B had not started reporting."],
    "next_questions": ["Does the one-week lead hold in a fresh quarter of data?",
                       "What is different about East that makes its swings so large?"],
}


@dataclass
class _FakeSession:
    prompt: str
    created: float
    replies: list[tuple[float, str]] = field(default_factory=list)
    report_requests: list[float] = field(default_factory=list)


_DEMO_PREFIX = "devin-demo-"
_DEMO_ID = re.compile(rf"{_DEMO_PREFIX}(\d+)-[0-9a-f]{{6}}")


class FakeDevin:
    """A scripted research run that advances with the clock, so the app works with no key."""

    def __init__(self, *, clock: Callable[[], float] = time.time, beat_seconds: float = 3.0):
        self._clock = clock
        self._beat = beat_seconds
        self._sessions: dict[str, _FakeSession] = {}
        self._lock = threading.Lock()

    def create_session(self, prompt: str, *, title: str, schema: dict, max_acu: int) -> SessionRef:
        created = self._clock()
        with self._lock:
            # The id carries its own start time, so a restarted server can replay the run from the id alone.
            session_id = f"{_DEMO_PREFIX}{int(created * 1000)}-{uuid.uuid4().hex[:6]}"
            self._sessions[session_id] = _FakeSession(prompt, created)
        return SessionRef(session_id, None)

    def get_session(self, session_id: str) -> SessionSnapshot:
        session, now = self._session(session_id), self._clock()
        beats = self._beats_played(session, now)
        steps: list[dict] = []
        artifacts: list[dict] = []
        conclusion = None
        for beat in beats:
            if beat.start:
                steps = [{**step, "state": "done"} for step in steps]
                steps.append({"id": beat.start[0], "label": beat.start[1], "state": "active"})
            if beat.artifact:
                artifacts.append(copy.deepcopy(beat.artifact))
            if beat.conclusion:
                steps = [{**step, "state": "done"} for step in steps]
                conclusion = copy.deepcopy(beat.conclusion)
        for number, (sent, _) in enumerate(session.replies, start=1):
            if now >= sent + 2 * self._beat:
                artifacts.append(_reply_artifact(number, steps[-1]["id"] if steps else None))
        # Replies and report requests are both answered two beats after they arrive.
        answered = [now >= sent + 2 * self._beat for sent in session.report_requests]
        running = len(beats) < len(SCRIPT) or not all(answered) or any(
            now < sent + 2 * self._beat for sent, _ in session.replies)
        output = {"steps": steps, "artifacts": artifacts, "conclusion": conclusion, "needs_user": None,
                  "report": _report(sum(answered)) if any(answered) else None}
        return SessionSnapshot("running" if running else "waiting", None, output)

    def list_messages(self, session_id: str) -> list[DevinMessage]:
        session, now = self._session(session_id), self._clock()
        timeline = [(session.created, f"{session_id}:prompt", "user", session.prompt)]
        for index, beat in enumerate(self._beats_played(session, now)):
            if beat.say:
                timeline.append((session.created + index * self._beat, f"{session_id}:b{index}", "devin", beat.say))
        for number, (sent, text) in enumerate(session.replies, start=1):
            timeline.append((sent, f"{session_id}:u{number}", "user", text))
            for offset, suffix, say in ((1, "ack", REPLY_ACK), (2, "done", REPLY_DONE)):
                if now >= sent + offset * self._beat:
                    timeline.append((sent + offset * self._beat, f"{session_id}:r{number}{suffix}", "devin", say))
        for number, sent in enumerate(session.report_requests, start=1):
            timeline.append((sent, f"{session_id}:q{number}", "user", REPORT_REQUEST))
            if now >= sent + 2 * self._beat:
                timeline.append((sent + 2 * self._beat, f"{session_id}:p{number}", "devin", REPORT_READY))
        timeline.sort(key=lambda entry: entry[0])
        return [DevinMessage(message_id, role, text, _iso(at)) for at, message_id, role, text in timeline]

    def send_message(self, session_id: str, text: str) -> None:
        session = self._session(session_id)
        with self._lock:
            if text == REPORT_REQUEST:
                session.report_requests.append(self._clock())
            else:
                session.replies.append((self._clock(), text))

    def list_attachments(self, session_id: str) -> list[Attachment]:
        self._session(session_id)
        return []

    def download(self, attachment: Attachment) -> tuple[bytes, str]:
        raise AttachmentRejected("the demo has no attachments")

    def _session(self, session_id: str) -> _FakeSession:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                match = _DEMO_ID.fullmatch(session_id)
                if match is None:
                    raise DevinUnavailable(f"unknown demo session {session_id}")
                session = self._sessions[session_id] = _FakeSession("", int(match.group(1)) / 1000)
        return session

    def _beats_played(self, session: _FakeSession, now: float) -> tuple[Beat, ...]:
        played = int(max(0.0, now - session.created) // self._beat) + 1
        return SCRIPT[:played]


def _reply_artifact(number: int, after_step: str | None) -> dict:
    return {
        "id": f"r{number}", "after_step": after_step, "type": "chart", "kind": "bar",
        "title": "Correlation by half of the sample", "headline": "holds in both",
        "x_label": "Half", "y_label": "r",
        "series": [{"name": "r", "points": [["First half", round(0.55 + 0.01 * number, 2)], ["Second half", 0.6]]}],
    }


def _report(number: int) -> dict:
    """The report as written for the `number`th request. Each rewrite reads differently,
    as Devin's would, so the app can tell a regenerated report from the one it already has."""
    report = copy.deepcopy(REPORT)
    if number > 1:
        report["summary"] += (f" This is revision {number}, written after looking back over the follow-up "
                              "conversation too, and the verdict has not changed.")
    return report
