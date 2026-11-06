"""Ollama: any question, short dialog memory.

Env: OLLAMA_URL (default http://127.0.0.1:11434), OLLAMA_MODEL (default: first installed model).
"""
import logging
import os
import time

from .http import get_json, post_json
from .i18n import SYSTEM_PROMPT, pick
from .text import clean

log = logging.getLogger("brain.llm")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "")
OLLAMA_TIMEOUT = 90            # the first request loads the model into memory - can be slow
HISTORY_TURNS = 6
HISTORY_TTL = 300              # seconds of silence after which the dialog is forgotten
AVAILABILITY_TTL = 20


class Ollama:
    def __init__(self, url=OLLAMA_URL, wanted_model=OLLAMA_MODEL):
        self.url = url
        self.wanted_model = wanted_model
        self._history = []                  # [(role, text)]
        self._history_t = 0.0
        self._avail = (False, 0.0, "")      # (ok, checked_at, model)

    def mark_down(self):
        self._avail = (False, time.time(), "")

    def model(self) -> str:
        """Model name if Ollama is reachable, else ''."""
        ok, ts, model = self._avail
        if time.time() - ts < AVAILABILITY_TTL:
            return model if ok else ""
        try:
            tags = get_json(self.url + "/api/tags", timeout=1.5)
            names = [m.get("name", "") for m in tags.get("models", []) if m.get("name")]
            names = [n for n in names if "embed" not in n.lower()]
            if self.wanted_model:
                found = self.wanted_model in names or (self.wanted_model + ":latest") in names
                model = self.wanted_model if found else ""
            else:
                model = names[0] if names else ""
            self._avail = (bool(model), time.time(), model)
            if model and not ok:
                log.info("Ollama available, model: %s", model)
            elif not model:
                log.warning("Ollama is running but the model is missing (installed: %s)", names)
        except Exception:
            self.mark_down()
            model = ""
        return model

    def ask(self, model: str, text: str, lang: str = "en") -> str:
        now = time.time()
        if now - self._history_t > HISTORY_TTL:
            self._history = []
        messages = [{"role": "system", "content": pick(SYSTEM_PROMPT, lang)}]
        messages += [{"role": r, "content": c} for r, c in self._history[-HISTORY_TURNS:]]
        messages.append({"role": "user", "content": text})
        data = post_json(self.url + "/api/chat", {
            "model": model, "messages": messages, "stream": False, "keep_alive": "30m",
            "options": {"temperature": 0.6, "num_predict": 200},
        }, OLLAMA_TIMEOUT)
        answer = clean(data.get("message", {}).get("content", ""))
        if answer:
            self._history += [("user", text), ("assistant", answer)]
            self._history = self._history[-HISTORY_TURNS * 2:]
            self._history_t = now
        return answer
