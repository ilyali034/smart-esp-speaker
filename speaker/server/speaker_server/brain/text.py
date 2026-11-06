"""Cleaning text for speech output."""
import re

MAX_REPLY_CHARS = 450          # longer replies take too long to speak


def plural_ru(n, one, few, many):
    n = abs(n) % 100
    if 11 <= n <= 19:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def clean(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*_#`>~|]", "", text)
    text = re.sub(r"\([^)]*\)", "", text)          # parentheses sound bad when spoken
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_REPLY_CHARS:
        cut = text[:MAX_REPLY_CHARS]
        end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        text = cut[:end + 1] if end > 80 else cut
    return text
