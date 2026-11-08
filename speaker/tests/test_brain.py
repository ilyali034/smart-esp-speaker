import os
import sys
import unittest
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from speaker.server.speaker_server import voices, wake  # noqa: E402
from speaker.server.speaker_server.brain import alarm, i18n, local, text, web  # noqa: E402


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

    def test_capabilities(self):
        self.assertIn("answer questions", local.handle("what can you do?", "en")[0])
        self.assertIn("отвечать на вопросы", local.handle("что ты можешь?", "ru")[0])

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


class TestAlarm(unittest.TestCase):
    def test_set_alarm_today_or_next_day(self):
        now = datetime.datetime(2026, 11, 6, 6, 0)
        result = alarm.parse_command("поставь будильник на 7:30", now)
        self.assertEqual(result["when"], now.replace(hour=7, minute=30))
        words = alarm.parse_command("разбуди меня в семь тридцать утра", now)
        self.assertEqual((words["when"].hour, words["when"].minute), (7, 30))
        spoken = alarm.parse_command("поставь будильник на семь часов тридцать минут", now)
        self.assertEqual((spoken["when"].hour, spoken["when"].minute), (7, 30))
        tomorrow = alarm.parse_command("заведи будильник на 5 утра", now)
        self.assertEqual(tomorrow["when"].date().day, 7)
        self.assertEqual((tomorrow["when"].hour, tomorrow["when"].minute), (5, 0))

    def test_set_alarm_english_time_suffix(self):
        now = datetime.datetime(2026, 11, 6, 8, 0)
        result = alarm.parse_command("set an alarm for 7 pm", now)
        self.assertEqual((result["when"].hour, result["when"].minute), (19, 0))

    def test_cancel_alarm(self):
        self.assertEqual(alarm.parse_command("отключи будильник"), {"action": "cancel"})
        self.assertEqual(alarm.parse_command("dismiss the alarm"), {"action": "cancel"})

    def test_invalid_or_unrelated_alarm_text(self):
        self.assertIsNone(alarm.parse_command("поставь будильник на 25:80"))
        self.assertIsNone(alarm.parse_command("расскажи про будильники"))


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


class TestWakeModels(unittest.TestCase):
    def test_parse_multiple_models(self):
        self.assertEqual(
            wake.parse_models("hey_jarvis, models/jarvis.onnx, models/dzharvis.onnx"),
            ["hey_jarvis", "models/jarvis.onnx", "models/dzharvis.onnx"],
        )

    def test_parse_model_sequence(self):
        self.assertEqual(wake.parse_models(["hey_jarvis", "models/jarvis.onnx"]),
                         ["hey_jarvis", "models/jarvis.onnx"])


if __name__ == "__main__":
    unittest.main()
