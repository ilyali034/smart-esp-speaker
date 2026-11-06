"""Per-language strings for the brain. Unknown language -> English."""

DEFAULT = "en"

LANG_NAMES = {"en": "English", "ru": "Russian"}

SYSTEM_PROMPT = {
    "en": ("You are the voice assistant of a smart speaker. Reply in English, briefly: one to three "
           "sentences. No lists, no markdown, no emoji, no links. Write so that it is easy to say "
           "aloud. If you do not know the answer, say so."),
    "ru": ("Ты голосовой помощник умной колонки. Отвечай по-русски, коротко: одно-три предложения. "
           "Без списков, без markdown, без эмодзи, без ссылок. Пиши так, чтобы это было удобно "
           "произносить вслух. Если не знаешь ответа, так и скажи."),
}

NOT_FOUND = {
    "en": "I could not find an answer. Check the internet or start Ollama.",
    "ru": "Не нашла ответа. Проверь интернет или запусти Ollama.",
}


def pick(table: dict, lang: str):
    return table.get(lang) or table[DEFAULT]
