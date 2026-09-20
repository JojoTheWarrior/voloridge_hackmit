# P2 reproducibility
Only modify this folder. Existing crawls and prereg.json are immutable inputs.
Container workflow: `docker build -t kingdom-polymarket-p2 .`, then
`docker run --rm -v "$PWD:/work" kingdom-polymarket-p2 python analyze.py`.
If Docker is unavailable, the supplied folder-local `.venv` is the fallback; no host system packages.
Run `python validate.py` after analysis. Acquisition is explicit via `python acquire.py`;
analysis and report rendering never fetch data. Public GET only, disk cache and one in-flight request.
