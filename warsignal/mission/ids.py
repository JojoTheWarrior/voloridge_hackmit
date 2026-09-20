from __future__ import annotations

import secrets
from datetime import datetime


def new_mission_id() -> str:
    return f"M{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3)}"
