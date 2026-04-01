"""
In-memory session manager with TTL.

Thread-safe, auto-cleanup of expired sessions.
Stores per-session memory for multi-turn agent interactions.
"""

import threading
import uuid
import time
from typing import Optional


class SessionManager:
    def __init__(self, ttl_seconds: int = 1800, max_sessions: int = 1000):
        self._store: dict = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds
        self._max_sessions = max_sessions

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        with self._lock:
            # Evict oldest if at capacity
            if len(self._store) >= self._max_sessions:
                self._cleanup_expired()
                if len(self._store) >= self._max_sessions:
                    oldest = min(self._store, key=lambda k: self._store[k]["last_accessed"])
                    del self._store[oldest]

            self._store[session_id] = {
                "created_at": time.time(),
                "last_accessed": time.time(),
                "memory": {
                    "region_id": None,
                    "intervention": None,
                    "last_intent": None,
                    "previous_queries": [],
                    "resolved_fields": [],
                }
            }
        return session_id

    def get_memory(self, session_id: str) -> Optional[dict]:
        with self._lock:
            session = self._store.get(session_id)
            if session is None:
                return None
            # Check TTL
            if time.time() - session["last_accessed"] > self._ttl:
                del self._store[session_id]
                return None
            session["last_accessed"] = time.time()
            return session["memory"].copy()

    def update_memory(self, session_id: str, updates: dict):
        with self._lock:
            session = self._store.get(session_id)
            if session is None:
                return
            session["last_accessed"] = time.time()
            memory = session["memory"]

            # Merge updates
            if updates.get("region_id"):
                memory["region_id"] = updates["region_id"]
            if updates.get("intervention"):
                memory["intervention"] = updates["intervention"]
            if updates.get("last_intent"):
                memory["last_intent"] = updates["last_intent"]
            if updates.get("query"):
                memory["previous_queries"].append(updates["query"])
                memory["previous_queries"] = memory["previous_queries"][-5:]  # keep last 5
            if updates.get("resolved_fields"):
                for field in updates["resolved_fields"]:
                    if field not in memory["resolved_fields"]:
                        memory["resolved_fields"].append(field)

    def get_or_create(self, session_id: Optional[str]) -> tuple:
        """Returns (session_id, memory). Creates new session if needed."""
        if session_id:
            memory = self.get_memory(session_id)
            if memory is not None:
                return session_id, memory
        # Create new
        new_id = self.create_session()
        return new_id, self.get_memory(new_id)

    def _cleanup_expired(self):
        """Remove expired sessions. Must be called with lock held."""
        now = time.time()
        expired = [
            sid for sid, data in self._store.items()
            if now - data["last_accessed"] > self._ttl
        ]
        for sid in expired:
            del self._store[sid]


# Singleton instance
session_manager = SessionManager()
