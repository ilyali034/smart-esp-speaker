"""Fast local commands (no LLM, no network), per language.

Add a command:
    @command("en", r"regex")
    def _name(match, text): return "answer"     # "" = stay silent, None = did not handle it
`text` is already lower-cased and stripped. Declaration order = priority; commands of the
detected language are tried first. handle() returns (answer, lang) of the matched command.
"""
import datetime
import re

from .text import plural_ru

_COMMANDS = []                 # (lang, compiled regex, full match?, function)

_MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "ru": ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
           "августа", "сентября", "октября", "ноября", "декабря"],
}
_WEEKDAYS = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "ru": ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"],
}


def command(lang, pattern, full=False):
    rx = re.compile(pattern)

    def deco(fn):
        _COMMANDS.append((lang, rx, full, fn))
        return fn
    return deco


def handle(text: str, lang: str = "en"):
    ordered = sorted(_COMMANDS, key=lambda c: c[0] != lang)     # stable: hinted language first
    for cmd_lang, rx, full, fn in ordered:
        m = rx.fullmatch(text) if full else rx.search(text)
        if m:
            ans = fn(m, text)
            if ans is not None:
                return ans, cmd_lang
    return None


# ------------------------------------------------------------------ English
@command("en", r"what(?:\W?s| is) the time|what time is it|current time|tell me the time|what time do you have")
def _time_en(m, text):
    now = datetime.datetime.now()
    return "It's %d:%02d %s" % (now.hour % 12 or 12, now.minute, "AM" if now.hour < 12 else "PM")


@command("en", r"what(?:\W?s| is) (?:the )?(?:today'?s )?date|what day is it|what day is today|what(?:\W?s| is) today")
def _date_en(m, text):
    d = datetime.date.today()
    return "Today is %s, %s %d, %d" % (_WEEKDAYS["en"][d.weekday()], _MONTHS["en"][d.month - 1], d.day, d.year)


@command("en", r"(hi|hello|hey|good morning|good afternoon|good evening)(?: there)?[\s!.,]*", full=True)
def _hello_en(m, text):
    return "Hello! I'm listening."


@command("en", r"(stop|enough|quiet|silence|cancel|never mind|shut up)[\s!.,]*", full=True)
def _stop_en(m, text):
    return ""                  # stay silent


# ------------------------------------------------------------------ Russian
@command("ru", r"сколько\s+(сейчас\s+)?времени|который\s+(сейчас\s+)?час|сколько\s+на\s+часах|текущее\s+время")
def _time_ru(m, text):
    now = datetime.datetime.now()
    h, mi = now.hour, now.minute
    return "Сейчас %d %s %d %s" % (h, plural_ru(h, "час", "часа", "часов"),
                                   mi, plural_ru(mi, "минута", "минуты", "минут"))


@command("ru", r"какое\s+(сегодня\s+)?число|какая\s+(сегодня\s+)?дата|какой\s+сегодня\s+день\s+недели|какой\s+сегодня\s+день")
def _date_ru(m, text):
    d = datetime.date.today()
    return "Сегодня %s, %d %s %d года" % (_WEEKDAYS["ru"][d.weekday()], d.day, _MONTHS["ru"][d.month - 1], d.year)


@command("ru", r"(привет|здравствуй|здравствуйте|добрый день|доброе утро|добрый вечер)[\s!.,]*", full=True)
def _hello_ru(m, text):
    return "Привет! Я слушаю."


@command("ru", r"(стоп|хватит|замолчи|тихо|отмена|не надо)[\s!.,]*", full=True)
def _stop_ru(m, text):
    return ""
