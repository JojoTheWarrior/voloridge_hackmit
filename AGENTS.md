# Development

- Use `docker compose up --build -d` for the isolated demo: UI at
  http://localhost:5173, API at http://localhost:8030. Demo state is in a
  separate Docker volume; this does not open or poll the local live database.
- Python checks: `docker compose exec api python -m pytest tests -q`.
- Web checks: `docker compose exec web npm test`, `docker compose exec web npm run lint`,
  and `docker compose exec web npm run build`.
- The compose stack forces fake Devin. Live validation needs an explicit
  spending limit and separate configuration; never bake credentials into images.
- Commit locally. Do not push or land changes on main unless requested.
- Preserve the explorer's opaque-origin sandbox; verify maps in the actual
  iframe with the server's content security policy.
