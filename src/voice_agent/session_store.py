from dataclasses import dataclass, field
from threading import Lock
from .schema import PAYEES_ALLOWED


@dataclass
class SessionState:
    payees_allowed: list[str] = field(default_factory=lambda: PAYEES_ALLOWED.copy())
    pending_transfer: dict | None = None
    screen: str = "home"


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = Lock()

    def get(self, session_id: str) -> SessionState:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionState()
            return self._sessions[session_id]


session_store = InMemorySessionStore()
