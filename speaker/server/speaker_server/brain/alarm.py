"""Parse simple spoken alarm commands into local one-shot alarm actions."""
import datetime
import re


_CANCEL = re.compile(
    r"\b(?:отключи|выключи|останови|сбрось|отмени)\b.*\bбудильник\b|"
    r"\b(?:turn\s+off|disable|stop|dismiss|cancel)\b.*\balarm\b|"
    r"\balarm\b.*\b(?:stop|off|cancel|dismiss)\b"
)
_INTENT = re.compile(r"\b(?:будильник|разбуди(?:ть)?\s+меня|alarm|wake\s+me(?:\s+up)?)\b")
_TIME = re.compile(
    r"(?<!\d)(\d{1,2})(?:(?:\s*[:.]\s*|\s+)(\d{2}))?"
    r"\s*(утра|вечера|дня|ночи|am|pm)?(?!\d)"
)
_NUMBER_WORDS = {
    "двадцать один": "21", "двадцать два": "22", "двадцать три": "23",
    "twenty one": "21", "twenty two": "22", "twenty three": "23",
    "ноль": "0", "один": "1", "одна": "1", "два": "2", "две": "2",
    "три": "3", "четыре": "4", "пять": "5", "шесть": "6", "семь": "7",
    "восемь": "8", "девять": "9", "десять": "10", "одиннадцать": "11",
    "двенадцать": "12", "тринадцать": "13", "четырнадцать": "14",
    "пятнадцать": "15", "шестнадцать": "16", "семнадцать": "17",
    "восемнадцать": "18", "девятнадцать": "19", "двадцать": "20",
    "тридцать": "30", "сорок": "40", "пятьдесят": "50",
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
    "nineteen": "19", "twenty": "20", "thirty": "30", "forty": "40",
    "fifty": "50",
}


def parse_command(text: str, now=None):
    """Return a cancel/set action, or None when text is not an alarm command.

    Set actions include the next local date/time, making an alarm scheduled after
    its requested time fire the following day. Time recognition deliberately
    accepts numeric forms such as ``7``, ``07:30`` and ``7 pm``.
    """
    normalized = text.lower().strip()
    if _CANCEL.search(normalized):
        return {"action": "cancel"}
    intent = _INTENT.search(normalized)
    if not intent:
        return None

    tail = normalized[intent.end():]
    for word, digits in sorted(_NUMBER_WORDS.items(), key=lambda item: -len(item[0])):
        tail = re.sub(r"\b" + re.escape(word) + r"\b", digits, tail)
    tail = re.sub(
        r"\b(\d{1,2})\s*час(?:а|ов)?\s+(\d{1,2})\s*минут(?:а|ы)?\b",
        r"\1:\2", tail,
    )
    match = _TIME.search(tail)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    suffix = match.group(3) or ""
    if suffix in ("вечера", "дня", "pm"):
        if hour < 1 or hour > 12:
            return None
        hour = hour % 12 + 12
    elif suffix in ("утра", "ночи", "am"):
        if hour < 1 or hour > 12:
            return None
        hour %= 12
    elif hour > 23:
        return None
    if minute > 59:
        return None

    current = now or datetime.datetime.now()
    when = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if when <= current:
        when += datetime.timedelta(days=1)
    return {"action": "set", "when": when}