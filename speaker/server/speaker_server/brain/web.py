"""Internet answers without an LLM: Wikipedia, then DuckDuckGo as a fallback."""
import logging
import re
import urllib.parse

from .http import get_json
from .text import clean

log = logging.getLogger("brain.web")

_TOPIC_RE = {
    "en": re.compile(
        r"^(?:please\s+)?(?:(?:can|could)\s+you\s+)?(?:tell\s+me\s+)?"
        r"(?:what\s+(?:is|are|was|were)|what(?:'s|\u2019s)|who\s+(?:is|are|was|were)|who(?:'s|\u2019s)|"
        r"what\s+does|what\s+do\s+you\s+know\s+about|tell\s+me\s+about|explain|define)\s+"
        r"(?:an?\s+|the\s+)?(.+)$", re.I),
    "ru": re.compile(
        r"^(?:скажи|расскажи|объясни|подскажи)?\s*(?:мне\s+)?"
        r"(?:что\s+такое|что\s+такая|что\s+такой|кто\s+такой|кто\s+такая|кто\s+такие|что\s+значит|"
        r"что\s+означает|расскажи\s+про|расскажи\s+о|расскажи\s+об|что\s+ты\s+знаешь\s+про|что\s+ты\s+знаешь\s+о)\s+(.+)$", re.I),
}

_DDG_REGION = {"en": "us-en", "ru": "ru-ru"}


def topic(t: str, lang: str = "en") -> str:
    t = t.strip(" ?!.,")
    rx = _TOPIC_RE.get(lang)
    m = rx.match(t) if rx else None
    out = (m.group(1) if m else t).strip(" ?!.,")
    if lang == "en":
        out = re.sub(r"\s+mean$", "", out)
    return out


def wikipedia(query: str, lang: str = "en") -> str:
    host = "https://%s.wikipedia.org" % lang
    q = urllib.parse.quote(query)
    s = get_json(host + "/w/api.php?action=query&list=search&format=json&srlimit=1&srsearch=" + q)
    hits = s.get("query", {}).get("search", [])
    if not hits:
        return ""
    title = hits[0]["title"]
    d = get_json(host + "/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_")))
    extract = d.get("extract", "")
    if not extract:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", clean(extract))
    return " ".join(sentences[:2])


def duckduckgo(query: str, lang: str = "en") -> str:
    q = urllib.parse.quote(query)
    kl = _DDG_REGION.get(lang, "wt-wt")
    d = get_json("https://api.duckduckgo.com/?format=json&no_html=1&skip_disambig=1&kl=%s&q=%s" % (kl, q))
    text = d.get("AbstractText") or d.get("Answer") or ""
    return clean(text) if isinstance(text, str) else ""


SOURCES = (("Wikipedia", wikipedia), ("DuckDuckGo", duckduckgo))


def answer(text: str, lang: str = "en") -> str:
    t = topic(text, lang)
    for name, fn in SOURCES:
        try:
            ans = fn(t, lang)
            if ans:
                log.info("answer from the web: %s", name)
                return ans
        except Exception as e:
            log.warning("%s unavailable: %s", name, e)
    return ""
