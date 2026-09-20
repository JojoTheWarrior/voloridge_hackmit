from __future__ import annotations

import time

import requests

from warsignal.config import env


class BrainUnavailable(RuntimeError):
    pass


class DevinBrain:
    base_url = "https://api.devin.ai"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or env("DEVIN_API_KEY")
        if not self.api_key:
            raise BrainUnavailable("DEVIN_API_KEY is not set")

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def create_session(self, prompt, *, title, tags, schema=None, max_acu=2):
        schema = dict(schema) if schema is not None else None
        if schema is not None:
            schema.setdefault("$schema", "http://json-schema.org/draft-07/schema#")
        body = {
            "prompt": prompt,
            "title": title,
            "tags": list(tags)[:50],
            "structured_output_schema": schema,
            "max_acu_limit": max_acu,
            "unlisted": False,
            "idempotent": False,
        }
        response = None
        for attempt in range(2):
            try:
                response = requests.post(
                    f"{self.base_url}/v1/sessions",
                    json=body,
                    headers=self.headers,
                    timeout=30,
                )
            except requests.RequestException as exc:
                raise BrainUnavailable(str(exc)) from exc
            if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                time.sleep(1)
                continue
            if response.status_code >= 400:
                detail = getattr(response, "text", "")[:300]
                raise BrainUnavailable(
                    f"Devin session creation failed ({response.status_code}): {detail}"
                )
            break
        if response is None:
            raise BrainUnavailable("Devin session creation failed")
        try:
            created = response.json()
            return created["session_id"], created["url"]
        except (ValueError, KeyError, TypeError) as exc:
            raise BrainUnavailable(f"invalid Devin session response: {exc}") from exc

    def ask_json(self, system, user, schema, *, title, tags, timeout_s=900, poll_s=8, max_acu=2):
        prompt = (
            f"{system}\n\n{user}\n\n"
            "You are a WarSignal mission brain. Do not clone repos or run code; "
            "reason from the text above only and reply ONLY via provide_structured_output "
            "matching the schema, then stop."
        )
        session_id, session_url = self.create_session(
            prompt,
            title=title,
            tags=tags,
            schema=schema,
            max_acu=max_acu,
        )
        required = schema.get("required", []) if isinstance(schema, dict) else []
        deadline = time.monotonic() + timeout_s
        while time.monotonic() <= deadline:
            try:
                status_response = requests.get(
                    f"{self.base_url}/v1/sessions/{session_id}",
                    headers=self.headers,
                    timeout=30,
                )
            except requests.RequestException as exc:
                raise BrainUnavailable(str(exc)) from exc
            if status_response.status_code >= 400:
                raise BrainUnavailable(f"Devin session status failed ({status_response.status_code})")
            try:
                status = status_response.json()
            except ValueError as exc:
                raise BrainUnavailable(f"invalid Devin status response: {exc}") from exc
            output = status.get("structured_output")
            if isinstance(output, dict) and all(key in output for key in required):
                output["_meta"] = {
                    "backend": "devin",
                    "session_id": session_id,
                    "session_url": status.get("url") or session_url,
                }
                return output
            if status.get("status_enum") in {"finished", "expired", "blocked"}:
                raise BrainUnavailable(
                    f"Devin session {status.get('status_enum')} without valid structured output"
                )
            time.sleep(min(poll_s, max(0, deadline - time.monotonic())))
        raise BrainUnavailable(f"Devin session timed out after {timeout_s}s")

    def ask_text(self, system, user, *, title, tags, timeout_s=900, poll_s=8, max_acu=2):
        schema = {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        }
        result = self.ask_json(
            system,
            user,
            schema,
            title=title,
            tags=tags,
            timeout_s=timeout_s,
            poll_s=poll_s,
            max_acu=max_acu,
        )
        return result["text"], result["_meta"]
