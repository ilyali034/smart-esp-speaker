"""Speech recognition (faster-whisper) with language detection restricted to the configured set."""
import logging

import numpy as np

log = logging.getLogger("stt")


class STT:
    def __init__(self, model_size="small", languages=("en", "ru"), device="cpu", compute_type="int8"):
        from faster_whisper import WhisperModel
        log.info("loading whisper %s (%s/%s), languages=%s...", model_size, device, compute_type, languages)
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.languages = tuple(languages)

    def _detect_language(self, audio: np.ndarray) -> str:
        """Most probable language among self.languages (Whisper may otherwise pick any of ~100)."""
        if len(self.languages) == 1:
            return self.languages[0]
        try:
            res = self.model.detect_language(audio)
            probs = res[2] if len(res) > 2 else None
            if probs:
                allowed = [(p, l) for l, p in probs if l in self.languages]
                if allowed:
                    return max(allowed)[1]
            if res[0] in self.languages:
                return res[0]
        except Exception as e:
            log.warning("language detection failed (%s), using %s", e, self.languages[0])
        return self.languages[0]

    def transcribe(self, pcm16: np.ndarray):
        """Returns (text, lang)."""
        audio = pcm16.astype(np.float32) / 32768.0
        lang = self._detect_language(audio)
        segments, _ = self.model.transcribe(
            audio, language=lang, vad_filter=True, beam_size=1,
            condition_on_previous_text=False,
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        return text, lang
