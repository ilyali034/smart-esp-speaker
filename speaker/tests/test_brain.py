import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from speaker_server import voices  # noqa: E402
from speaker_server.brain import i18n, local, text, web  # noqa: E402


class TestText(unittest.TestCase):
    def test_plural_ru(self):
        self.assertEqual(text.plural_ru(1, "час", "часа", "часов"), "час")
        self.assertEqual(text.plural_ru(3, "час", "часа", "часов"), "часа")
        self.assertEqual(text.plural_ru(5, "час", "часа", "часов"), "часов")
        self.assertEqual(text.plural_ru(11, "час", "часа", "часов"), "часов")
        self.assertEqual(text.plural_ru(21, "час", "часа", "часов"), "час")

    def test_clean(self):
        self.assertEqual(text.clean("**Hello** (aside) http://x.y world"), "Hello world")
        self.assertEqual(text.clean("<think>x</think>Answer"), "Answer")

    def test_clean_truncates_on_sentence(self):
        out = text.clean(("This is sentence number one. " * 40).strip())
        self.assertLessEqual(len(out), text.MAX_REPLY_CHARS)
        self.assertTrue(out.endswith("."))


class TestLocal(unittest.TestCase):
    def test_time_en(self):
        ans, lang = local.handle("what time is it?", "en")
        self.assertTrue(ans.startswith("It's"))
        self.assertEqual(lang, "en")

    def test_time_ru(self):
        ans, lang = local.handle("сколько времени", "ru")
        self.assertTrue(ans.startswith("Сейчас"))
        self.assertEqual(lang, "ru")

    def test_date(self):
        self.assertTrue(local.handle("what's the date", "en")[0].startswith("Today is"))
        self.assertTrue(local.handle("какое сегодня число", "ru")[0].startswith("Сегодня"))

    def test_language_follows_matched_command(self):
        # STT said "en" but the phrase is Russian: the reply language must be Russian
        self.assertEqual(local.handle("привет!", "en"), ("Привет! Я слушаю.", "ru"))
        self.assertEqual(local.handle("hello", "ru"), ("Hello! I'm listening.", "en"))

    def test_stop_is_silence(self):
        self.assertEqual(local.handle("stop.", "en"), ("", "en"))
        self.assertEqual(local.handle("стоп.", "ru"), ("", "ru"))

    def test_no_match(self):
        self.assertIsNone(local.handle("tell me about cats", "en"))
        self.assertIsNone(local.handle("расскажи про кошек", "ru"))


class TestWeb(unittest.TestCase):
    def test_topic_en(self):
        self.assertEqual(web.topic("What is a black hole?", "en"), "black hole")
        self.assertEqual(web.topic("who is Albert Einstein", "en"), "Albert Einstein")
        self.assertEqual(web.topic("tell me about Python", "en"), "Python")
        self.assertEqual(web.topic("what does entropy mean", "en"), "entropy")
        self.assertEqual(web.topic("Python", "en"), "Python")

    def test_topic_ru(self):
        self.assertEqual(web.topic("что такое черная дыра?", "ru"), "черная дыра")
        self.assertEqual(web.topic("расскажи про Python", "ru"), "Python")


class TestI18n(unittest.TestCase):
    def test_fallback_to_english(self):
        self.assertEqual(i18n.pick(i18n.NOT_FOUND, "de"), i18n.NOT_FOUND["en"])


class TestVoices(unittest.TestCase):
    def test_cli_and_env(self):
        env = {"PIPER_MODEL": "any.onnx", "PIPER_MODEL_EN": "en_env.onnx", "PIPER_MODEL_RU": "ru_env.onnx"}
        v = voices.collect_voice_specs(["ru=ru_cli.onnx"], env)
        self.assertEqual(v, {"*": "any.onnx", "en": "en_env.onnx", "ru": "ru_cli.onnx"})

    def test_bare_path_is_any(self):
        self.assertEqual(voices.collect_voice_specs(["voice.onnx"], {}), {"*": "voice.onnx"})


if __name__ == "__main__":
    unittest.main()
