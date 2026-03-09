"""
Council - Context Manager
Maintains the single shared conversation history across all models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json


MODEL_COLORS = {
    "user":   "#E0E0E0",
    "claude": "#FF8C42",
    "gpt":    "#4CAF82",
    "gemini": "#4A9EFF",
    "system": "#888888",
}

MODEL_LABELS = {
    "user":   "YOU",
    "claude": "CLAUDE",
    "gpt":    "GPT",
    "gemini": "GEMINI",
    "system": "SYSTEM",
}


@dataclass
class Message:
    role: str          # "user", "claude", "gpt", "gemini", "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    model_target: Optional[str] = None   # which model was addressed

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }


class ContextManager:
    def __init__(self, max_messages: int = 200):
        self.history: list[Message] = []
        self.max_messages = max_messages

    def add(self, role: str, content: str, model_target: str = None) -> Message:
        msg = Message(role=role, content=content, model_target=model_target)
        self.history.append(msg)
        if len(self.history) > self.max_messages:
            # Keep system context, trim oldest non-system
            non_system = [m for m in self.history if m.role != "system"]
            self.history = self.history[:1] + non_system[-(self.max_messages - 1):]
        return msg

    def get_for_model(self, model: str) -> list[dict]:
        """
        Format the shared history for a specific model's API.
        Returns list of {role, content} dicts normalized for OpenAI-style APIs.
        Claude and Gemini adapters will reformat as needed.
        """
        formatted = []
        for msg in self.history:
            if msg.role == "system":
                continue
            if msg.role == "user":
                formatted.append({"role": "user", "content": msg.content})
            else:
                # Other models' responses appear as assistant turns, labeled
                label = MODEL_LABELS.get(msg.role, msg.role.upper())
                formatted.append({
                    "role": "assistant",
                    "content": f"[{label}]: {msg.content}"
                })
        return formatted

    def get_system_prompt(self, model: str) -> str:
        model_label = MODEL_LABELS.get(model, model.upper())
        return (
            f"You are {model_label}, part of a multi-AI council. "
            "Other AI models (Claude, GPT, Gemini) are also in this conversation and you can see their responses labeled with [MODEL_NAME]:. "
            "Collaborate, build on each other's ideas, and disagree when you have a better solution. "
            "Be concise. Do not repeat what others already said unless you're correcting it. "
            "You are speaking to a developer — be technical and direct."
        )

    def clear(self):
        self.history = []

    def export_json(self) -> str:
        return json.dumps([m.to_dict() for m in self.history], indent=2)

    def summary_stats(self) -> dict:
        counts = {}
        for msg in self.history:
            counts[msg.role] = counts.get(msg.role, 0) + 1
        return counts
