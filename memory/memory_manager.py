"""
Memory management system — session + persistent + LangGraph checkpointing.
100% free, no external DB required. Uses local JSON files for persistence.
"""

import json
import os
import hashlib
from datetime import datetime
from typing import Optional
from langgraph.checkpoint.memory import MemorySaver


class SessionMemory:
    """In-memory storage for the current conversation session."""

    def __init__(self):
        self.messages = []
        self.profile_data = None
        self.profile_url = None
        self.career_goals = []
        self.analyzed_jobs = []
        self.session_start = datetime.now().isoformat()
        self.last_intent = None

    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

    def get_recent_messages(self, n: int = 10) -> list:
        return self.messages[-n:]

    def get_conversation_summary(self) -> str:
        recent = self.get_recent_messages(6)
        if not recent:
            return "No previous conversation in this session."
        lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"]
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def set_profile(self, profile_data: dict, url: str = ""):
        self.profile_data = profile_data
        self.profile_url = url

    def add_career_goal(self, goal: str):
        if goal and goal not in self.career_goals:
            self.career_goals.append(goal)

    def add_analyzed_job(self, job_role: str, score: str = ""):
        self.analyzed_jobs.append({
            "role": job_role,
            "score": score,
            "analyzed_at": datetime.now().isoformat(),
        })

    def to_dict(self) -> dict:
        return {
            "messages": self.messages,
            "profile_url": self.profile_url,
            "career_goals": self.career_goals,
            "analyzed_jobs": self.analyzed_jobs,
            "session_start": self.session_start,
        }


class PersistentMemory:
    """File-based persistent storage. No database needed — just JSON files."""

    def __init__(self, storage_dir: str = ".memory_store"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def _get_user_file(self, key: str) -> str:
        safe_key = hashlib.md5(key.encode()).hexdigest()[:12]
        return os.path.join(self.storage_dir, f"user_{safe_key}.json")

    def save(self, key: str, data: dict):
        filepath = self._get_user_file(key)
        existing = self.load(key) or {}
        existing.update(data)
        existing["last_updated"] = datetime.now().isoformat()
        with open(filepath, "w") as f:
            json.dump(existing, f, indent=2, default=str)

    def load(self, key: str) -> Optional[dict]:
        filepath = self._get_user_file(key)
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def get_summary(self, key: str) -> str:
        data = self.load(key)
        if not data:
            return "New user — no previous session data."
        lines = [f"Returning user (session #{data.get('total_sessions', 1)})"]
        if data.get("career_goals"):
            lines.append(f"Known goals: {', '.join(data['career_goals'])}")
        if data.get("analyzed_jobs"):
            roles = [j.get("role", "") for j in data["analyzed_jobs"][-3:]]
            lines.append(f"Previously analyzed: {', '.join(roles)}")
        return "\n".join(lines)

    def end_session(self, key: str, session: SessionMemory):
        existing = self.load(key) or {}
        data = {
            "career_goals": session.career_goals,
            "analyzed_jobs": session.analyzed_jobs,
            "total_sessions": existing.get("total_sessions", 0) + 1,
            "first_seen": existing.get("first_seen", datetime.now().isoformat()),
            "profile_name": session.profile_data.get("full_name", "") if session.profile_data else "",
        }
        self.save(key, data)


class MemoryManager:
    """Unified memory interface for all agents."""

    def __init__(self):
        self.session = SessionMemory()
        self.persistent = PersistentMemory()
        self.checkpointer = MemorySaver()  # LangGraph graph-level checkpointing

    def add_user_message(self, content: str):
        self.session.add_message("user", content)

    def add_assistant_message(self, content: str):
        self.session.add_message("assistant", content)

    def set_profile(self, profile_data: dict, url: str = ""):
        self.session.set_profile(profile_data, url)
        mem_key = url or profile_data.get("full_name", "anonymous")
        self.persistent.save(mem_key, {
            "profile_url": url,
            "profile_name": profile_data.get("full_name", ""),
            "profile_headline": profile_data.get("headline", ""),
        })

    def get_full_context(self) -> dict:
        profile_summary = "No profile loaded yet."
        if self.session.profile_data:
            p = self.session.profile_data
            profile_summary = (
                f"{p.get('full_name', 'User')} — {p.get('headline', 'N/A')} "
                f"in {p.get('location', 'N/A')}"
            )

        mem_context = self.session.get_conversation_summary()

        mem_key = self.session.profile_url or ""
        if mem_key:
            persistent_ctx = self.persistent.get_summary(mem_key)
            mem_context = f"[Persistent Memory]\n{persistent_ctx}\n\n[This Session]\n{mem_context}"

        return {
            "profile_summary": profile_summary,
            "career_goals": ", ".join(self.session.career_goals) or "Not specified yet",
            "memory_context": mem_context,
            "has_profile": self.session.profile_data is not None,
            "profile_data": self.session.profile_data,
        }

    def get_messages_for_api(self) -> list:
        """Return last 20 messages formatted for Gemini multi-turn chat."""
        recent = self.session.get_recent_messages(20)
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    def save_session_end(self):
        key = self.session.profile_url or "anonymous"
        self.persistent.end_session(key, self.session)