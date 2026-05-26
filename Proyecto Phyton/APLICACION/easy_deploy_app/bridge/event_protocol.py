from __future__ import annotations

import json
import sys
import threading
import uuid
from datetime import datetime


def new_id() -> str:
    return str(uuid.uuid4())


class EventSink:
    """Emite eventos JSON Lines al proceso Electron."""

    def __init__(self, stream=None):
        self._stream = stream or sys.__stdout__
        self._lock = threading.Lock()

    def emit(self, event_type: str, **payload):
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            **payload,
        }
        text = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            buffer = getattr(self._stream, "buffer", None)
            if buffer is not None:
                buffer.write((text + "\n").encode("utf-8"))
                buffer.flush()
            else:
                self._stream.write(text + "\n")
                self._stream.flush()
