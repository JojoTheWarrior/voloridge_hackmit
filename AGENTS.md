# Development

- Use `docker compose up --build -d` for real Devin: UI at
  http://localhost:5173, API at http://localhost:8030, existing `.kingdom` database.
- Python checks: `docker compose exec api python -m pytest tests -q`.
- Web checks: `docker compose exec web npm test`, `docker compose exec web npm run lint`,
  and `docker compose exec web npm run build`.
- Compose uses the local gitignored `.env` key and caps each mission at 5 ACU.
  Tom approved this live configuration. For an isolated scripted demo, use
  `docker compose -f compose.yaml -f compose.demo.yaml up -d`; it replaces the
  same API container and uses a separate Docker volume.
  Never bake credentials into images.
- Commit locally. Do not push or land changes on main unless requested.
- Preserve the explorer's opaque-origin sandbox; verify maps in the actual
  iframe with the server's content security policy.
