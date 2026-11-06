"""Speech synthesis: Piper via command line, one voice per language."""
import json
import logging
import os
import subprocess

import numpy as np

from ..audio import RATE, beep, resample
from ..voices import ANY

log = logging.getLogger("tts")


class TTS:
    """voices: {lang: path to .onnx}. Without a voice for the language, a beep is played instead."""

    def __init__(self, voices=None, piper_bin="piper"):
        self.piper_bin = piper_bin
        self.voices = {}                    # lang -> (path, sample_rate)
        for lang, path in (voices or {}).items():
            rate = 22050
            cfg = path + ".json"
            if os.path.exists(cfg):
                with open(cfg, encoding="utf-8") as f:
                    rate = json.load(f)["audio"]["sample_rate"]
            self.voices[lang] = (path, rate)
        if not self.voices:
            log.warning("no Piper voice configured: a plain beep will be played instead of speech")

    def has_voice(self, lang: str) -> bool:
        return lang in self.voices or ANY in self.voices

    def synthesize(self, text: str, lang: str = "en") -> np.ndarray:
        """Returns PCM16 mono 16 kHz."""
        voice = self.voices.get(lang) or self.voices.get(ANY)
        if not voice or not text:
            if text:
                log.warning("no Piper voice for language %r", lang)
            return beep()
        path, src_rate = voice
        proc = subprocess.run(
            [self.piper_bin, "--model", path, "--output-raw"],
            input=text.encode("utf-8"), capture_output=True, timeout=60,
            env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"),  # else Windows feeds Piper stdin in cp125x -> garbage
        )
        if proc.returncode != 0:
            log.error("piper failed (code %s): %s", proc.returncode,
                      proc.stderr.decode(errors="replace")[-1200:])
            return beep(300, 400)
        pcm = np.frombuffer(proc.stdout, dtype=np.int16)
        return resample(pcm, src_rate, RATE)
