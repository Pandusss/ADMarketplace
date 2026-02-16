"""
Main Server Entry Point.
Initializes the FastAPI application and starts the Uvicorn ASGI server 
with the configured host, port, and worker settings.
"""
from __future__ import annotations

import uvicorn


def main() -> None:
    # One-command local run (similar to "python app.py" in Flask projects).
    # IMPORTANT: keep reload=False because this app runs Telegram polling (getUpdates),
    # and reload can briefly run two instances, causing Telegram "Conflict" errors.
    # proxy_headers=True is needed to correctly handle Origin/Host when running behind a tunnel (cloudflared).
    uvicorn.run("app.main:app", host="0.0.0.0", port=5002, reload=False, proxy_headers=True, forwarded_allow_ips="127.0.0.1")


if __name__ == "__main__":
    main()

