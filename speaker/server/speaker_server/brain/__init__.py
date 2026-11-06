"""Answer logic of the speaker.

respond(text, lang) -> Reply(text, lang); empty text = stay silent.
Order: local commands -> Ollama -> web (Wikipedia, DuckDuckGo).
`lang` is the language detected by STT; the reply language selects the TTS voice.
"""
import logging
from typing import NamedTuple

from . import local, web
from .i18n import NOT_FOUND, pick
from .llm import Ollama

log = logging.getLogger("brain")

_llm = Ollama()


class Reply(NamedTuple):
    text: str
    lang: str


def respond(text: str, lang: str = "en") -> Reply:
    t = text.lower().strip()
    if not t:
        return Reply("", lang)

    hit = local.handle(t, lang)
    if hit is not None:
        return Reply(*hit)

    model = _llm.model()
    if model:
        try:
            ans = _llm.ask(model, text, lang)
            if ans:
                return Reply(ans, lang)
        except Exception as e:
            log.warning("Ollama did not answer (%s), trying the web", e)
            _llm.mark_down()

    ans = web.answer(text, lang)
    return Reply(ans or pick(NOT_FOUND, lang), lang)
