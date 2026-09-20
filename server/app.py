from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException

from server.brief import OUTPUT_SCHEMA, build_prompt, derive_title, session_title
from server.devin import AttachmentRejected, DevinClient, DevinUnavailable, devin_mode, make_client, max_acu
from server.poller import Poller
from server.store import MissionRow, Store

log = logging.getLogger(__name__)

NO_SESSION = "This mission never reached Devin, so there is nothing to reply to. Start a new mission instead."


class Invalid(Exception):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


class NotFound(Exception):
    pass


def create_app(store: Store, client: DevinClient, *, demo: bool) -> Flask:
    app = Flask(__name__)
    app.json.sort_keys = False

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

    @app.post("/api/missions")
    def create_mission():
        body = _body()
        hypothesis = _text(body.get("hypothesis"))
        if not hypothesis:
            raise Invalid("hypothesis", "Describe a connection to test")
        requested = body.get("datasetIds")
        datasets = store.get_datasets(i for i in requested if isinstance(i, str)) if isinstance(requested, list) else []
        reference = _text(body.get("reference")) or None
        title = derive_title(hypothesis)
        prompt = build_prompt(hypothesis, datasets, reference)
        mission = store.create_mission(
            hypothesis, title=title, dataset_ids=[d["id"] for d in datasets], reference=reference, prompt=prompt
        )
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
        mission = require_mission(mission_id)
        text = _text(_body().get("text"))
        if not text:
            raise Invalid("text", "Write a reply")
        store.append_event(mission_id, "user_message", {"text": text})
        if not mission.session_id:
            store.append_event(mission_id, "error", {"text": NO_SESSION})
            return jsonify({}), 202
        try:
            client.send_message(mission.session_id, text)
        except DevinUnavailable as exc:
            store.append_event(mission_id, "error", {"text": f"That reply did not reach Devin: {exc}"})
        else:
            store.reopen(mission_id)
        return jsonify({}), 202

    @app.post("/api/missions/<mission_id>/done")
    def mark_done(mission_id: str):
        require_mission(mission_id)
        store.mark_done(mission_id)
        return jsonify({})

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
    body["events"] = store.list_events(mission_id)
    return body
