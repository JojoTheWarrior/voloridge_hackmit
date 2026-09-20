from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import quote, urlsplit

from flask import Flask, Response, jsonify, request, send_file
from werkzeug.exceptions import HTTPException

from server.autonomy import CONTINUE
from server.brief import (
    OUTPUT_SCHEMA,
    REPORT_REQUEST,
    build_explorer_request,
    build_prompt,
    derive_title,
    session_title,
)
from server.devin import (
    AttachmentRejected,
    DevinClient,
    DevinUnavailable,
    devin_mode,
    make_client,
    max_acu,
)
from server.explorer import (
    DOCUMENT_EXTENSIONS,
    KIT_DIR,
    content_type,
    extension,
    read_kit,
    site_file,
)
from server.poller import Poller
from server.research import MAX_REFERENCE_CHARS, RESEARCH_DIR, list_findings
from server.store import MissionRow, Store

log = logging.getLogger(__name__)

NO_SESSION = "This mission never reached Devin, so there is nothing to reply to. Start a new mission instead."
NO_SESSION_REPORT = "This mission never reached Devin, so there is nothing to report on. Start a new mission instead."
NO_SESSION_EXPLORER = "This mission never reached Devin, so there is nothing to explore. Start a new mission instead."
MAX_INSTRUCTIONS = 2000

# An explorer is code Devin wrote. Its frame has an opaque origin, so its own relative fetches are
# cross-origin and need the CORS header; the policy sandboxes it the same way when it is opened directly.
EXPLORER_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
}
_ORIGIN = re.compile(r"https?://[A-Za-z0-9.\-\[\]:]+")


def explorer_csp(origin: str) -> str:
    """The policy for a served explorer document. It names our own origin rather than 'self': a document
    sandboxed without allow-same-origin has an opaque origin, and 'self' then matches nothing, which
    would block the explorer's own kit and data files."""
    own = origin if _ORIGIN.fullmatch(origin) else ""
    return (
        "sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox; "
        f"default-src {own} data: blob:; "
        f"script-src {own} 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        f"style-src {own} 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        f"font-src {own} data: https://fonts.gstatic.com; "
        "img-src * data: blob:; connect-src *; worker-src blob:; child-src blob:"
    ).replace("  ", " ")


def browser_origin() -> str:
    """The origin the browser addressed, which behind a proxy is not the Host this server sees."""
    host = request.headers.get("X-Forwarded-Host", "")
    scheme = request.headers.get("X-Forwarded-Proto", "http")
    forwarded = f"{scheme}://{host}"
    return forwarded if host and _ORIGIN.fullmatch(forwarded) else request.host_url.rstrip("/")


class Invalid(Exception):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


class NotFound(Exception):
    pass


def create_app(store: Store, client: DevinClient, *, demo: bool, kit_dir: Path = KIT_DIR, research_dir: Path = RESEARCH_DIR) -> Flask:
    app = Flask(__name__)
    app.json.sort_keys = False

    @app.after_request
    def explorer_headers(response: Response) -> Response:
        if request.endpoint == "explorer_file":
            response.headers.update(EXPLORER_HEADERS)
        return response

    @app.errorhandler(Invalid)
    def invalid(error: Invalid):
        return jsonify(field=error.field, message=error.message), 422

    @app.errorhandler(NotFound)
    def not_found(error: NotFound):
        return jsonify(message=str(error)), 404

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        return jsonify(message=error.description), error.code

    def require_mission(mission_id: str) -> MissionRow:
        mission = store.get_mission(mission_id)
        if mission is None:
            raise NotFound("Mission not found")
        return mission

    @app.get("/api/meta")
    def meta():
        return jsonify(demo=demo, maxAcu=max_acu(), devinMode=devin_mode())

    @app.get("/api/missions")
    def list_missions():
        return jsonify([_summary(mission) for mission in store.list_missions()])

    @app.get("/api/research")
    def research():
        return jsonify(list_findings(research_dir))

    @app.post("/api/missions")
    def create_mission():
        body = _body()
        hypothesis = _text(body.get("hypothesis"))
        if not hypothesis:
            raise Invalid("hypothesis", "Describe a connection to test")
        requested = body.get("datasetIds")
        datasets = store.get_datasets(i for i in requested if isinstance(i, str)) if isinstance(requested, list) else []
        reference = _text(body.get("reference")) or None
        if reference and len(reference) > MAX_REFERENCE_CHARS:
            raise Invalid("reference", "Keep research under 100,000 characters")
        title = derive_title(hypothesis)
        prompt = build_prompt(hypothesis, datasets, reference)
        mission = store.create_mission(
            hypothesis, title=title, dataset_ids=[d["id"] for d in datasets], reference=reference, prompt=prompt
        )
        store.set_autonomy(mission.id, auto_phase="research")
        store.append_event(mission.id, "user_message", {"text": hypothesis})
        try:
            session = client.create_session(
                prompt, title=session_title(title), schema=OUTPUT_SCHEMA, max_acu=max_acu()
            )
        except DevinUnavailable as exc:
            # The user sees what happened in the thread instead of a 5xx.
            store.fail(mission.id, f"Could not start a Devin session: {exc}")
        else:
            store.set_session(mission.id, session.session_id, session.url)
        return jsonify(_mission(store, mission.id)), 201

    @app.get("/api/missions/<mission_id>")
    def get_mission(mission_id: str):
        require_mission(mission_id)
        return jsonify(_mission(store, mission_id))

    @app.post("/api/missions/<mission_id>/messages")
    def send_message(mission_id: str):
        require_mission(mission_id)
        text = _text(_body().get("text"))
        if not text:
            raise Invalid("text", "Write a reply")
        with store.run_lock(mission_id):
            mission = require_mission(mission_id)
            if not mission.session_id:
                return jsonify(message=NO_SESSION), 409
            # Older sessions received the previous, approval-driven brief. Upgrade them on a reply.
            outgoing = text if mission.auto_phase else f"{CONTINUE}\n\nLatest user direction:\n{text}"
            try:
                client.send_message(mission.session_id, outgoing)
            except DevinUnavailable as exc:
                return jsonify(message=f"Could not confirm delivery to Devin: {exc}"), 503
            store.append_event(mission_id, "user_message", {"text": text})
            if not mission.auto_phase:
                store.set_autonomy(mission_id, auto_phase="research")
            store.reopen(mission_id)
        return jsonify({}), 202

    @app.post("/api/missions/<mission_id>/done")
    def mark_done(mission_id: str):
        require_mission(mission_id)
        with store.run_lock(mission_id):
            store.mark_done(mission_id)
        return jsonify({})

    @app.post("/api/missions/<mission_id>/report")
    def request_report(mission_id: str):
        mission = require_mission(mission_id)
        if mission.report_pending:
            return jsonify({}), 202
        if not mission.session_id:
            store.append_event(mission_id, "error", {"text": NO_SESSION_REPORT})
            return jsonify({}), 202
        try:
            client.send_message(mission.session_id, REPORT_REQUEST)
        except DevinUnavailable as exc:
            store.append_event(mission_id, "error", {"text": f"The report request did not reach Devin: {exc}"})
        else:
            store.request_report(mission_id)
        return jsonify({}), 202

    @app.post("/api/missions/<mission_id>/explorer")
    def request_explorer(mission_id: str):
        mission = require_mission(mission_id)
        instructions = _text(_body().get("instructions")) or None
        if instructions and len(instructions) > MAX_INSTRUCTIONS:
            raise Invalid("text", "Keep instructions under 2,000 characters")
        if mission.explorer_pending:
            return jsonify({}), 202
        if not mission.session_id:
            store.append_event(mission_id, "error", {"text": NO_SESSION_EXPLORER})
            return jsonify({}), 202
        message = build_explorer_request(
            instructions, read_kit(kit_dir), next_version=mission.explorer_seen_version + 1)
        try:
            client.send_message(mission.session_id, message)
        except DevinUnavailable as exc:
            store.append_event(mission_id, "error", {"text": f"The explorer request did not reach Devin: {exc}"})
        else:
            store.request_explorer(mission_id)
        return jsonify({}), 202

    @app.get("/api/missions/<mission_id>/explorer/<int:version>/<path:path>")
    def explorer_file(mission_id: str, version: int, path: str):
        require_mission(mission_id)
        file = site_file(store.explorer_dir(mission_id, version), path, kit_dir)
        if file is None:
            raise NotFound("File not found")
        response = send_file(file, mimetype=content_type(path), conditional=False, max_age=None)
        if extension(path) in DOCUMENT_EXTENSIONS:
            response.headers["Content-Security-Policy"] = explorer_csp(browser_origin())
        return response

    @app.get("/api/missions/<mission_id>/attachments/<name>")
    def attachment(mission_id: str, name: str):
        mission = require_mission(mission_id)
        try:
            # Only files Devin attached to this mission's own session are ever fetched.
            listed = client.list_attachments(mission.session_id) if mission.session_id else []
            match = next((item for item in listed if item.name == name), None)
            if match is None:
                raise NotFound("Attachment not found")
            data, content_type = client.download(match)
        except (DevinUnavailable, AttachmentRejected) as exc:
            log.warning("attachment %r of mission %s refused: %s", name, mission_id, exc)
            raise NotFound("Attachment not found") from exc
        return Response(data, mimetype=content_type, headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=3600",
        })

    @app.get("/api/datasets")
    def list_datasets():
        return jsonify(store.list_datasets())

    @app.post("/api/datasets")
    def link_dataset():
        body = _body()
        name, url = _text(body.get("name")), _text(body.get("url"))
        if not name:
            raise Invalid("name", "Enter a name")
        if not _is_http_url(url):
            raise Invalid("url", "Enter an http or https URL")
        return jsonify(store.add_dataset(name, url)), 201

    return app


def serve(host: str, port: int, db: str | Path) -> None:
    store = Store(db)
    client, demo = make_client()
    # Existing live sessions still have the older brief. Adopt them once; completed history stays closed.
    for mission in store.live_missions():
        if not mission.auto_phase and mission.status in ("working", "waiting"):
            store.set_autonomy(mission.id, auto_phase="adopt")
    Poller(store, client).start()
    print(f"Kingdom server on http://{host}:{port} ({'demo mode' if demo else 'live Devin'})")
    create_app(store, client, demo=demo).run(host=host, port=port, threaded=True)


def _body() -> dict:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _is_http_url(value: str) -> bool:
    parts = urlsplit(value)
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def _summary(mission: MissionRow) -> dict:
    return {
        "id": mission.id,
        "title": mission.title,
        "hypothesis": mission.hypothesis,
        "status": mission.status,
        "createdAt": mission.created_at,
        "updatedAt": mission.updated_at,
    }


def _mission(store: Store, mission_id: str) -> dict:
    mission = store.get_mission(mission_id)
    body = {**_summary(mission), "datasetIds": mission.dataset_ids}
    if mission.session_url:
        body["sessionUrl"] = mission.session_url
    if mission.needs_user:
        body["needsUser"] = mission.needs_user
    if mission.report:
        body["report"] = mission.report
    body["reportPending"] = mission.report_pending
    if mission.explorer:
        build = mission.explorer
        body["explorer"] = {
            "version": build["version"],
            "title": build["title"],
            "description": build["description"],
            "src": f"/api/missions/{mission.id}/explorer/{build['version']}/{quote(build['entry'])}",
            "builtAt": build["builtAt"],
        }
    body["explorerPending"] = mission.explorer_pending
    body["events"] = store.list_events(mission_id)
    return body
