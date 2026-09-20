All generated files and caches stay in this directory. Public read-only GET / read-only RPC or GraphQL queries only. Never use a signer or wallet. No identity linkage.
Container: docker build -t polymarket-experts . ; docker run --rm -v "$PWD:/work" polymarket-experts
If the pre-existing Docker daemon is unavailable, use the pre-existing .venv; never install host system packages. Preserve prereg.json and prereg.sha256 byte-for-byte.
