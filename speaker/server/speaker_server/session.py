"""One connected speaker: state machine idle -> listening -> thinking -> speaking."""
import asyncio
import json
import logging
import time
import wave

import numpy as np
import websockets

from . import brain
from .audio import RATE

log = logging.getLogger("session")

SPEAK_LEAD_S = 0.4               # how many seconds of audio the server sends ahead of playback
BARGE_DEAF_S = 0.35              # ignore audio after an interruption: the speaker still plays the tail
WAKE_FRAME = 1280                # openWakeWord works on 80 ms frames
SEND_CHUNK = 4096                # bytes of audio per frame sent to the speaker


class Session:
    def __init__(self, ws, app):
        self.ws = ws
        self.app = app
        self.name = "?"
        self.state = "idle"
        self.muted = False
        self.wake_buf = np.zeros(0, dtype=np.int16)
        self._reset_listen()
        self._job = None
        self._interrupted = False
        self._deaf_until = 0.0
        self._m_t, self._m_rms, self._m_score = time.time(), 0.0, 0.0
        self._dump, self._dump_n = [], 0

    # ---------------------------------------------------------- diagnostics
    def _dump_audio(self, pcm):
        """--dump-wav N: writes N seconds of audio to dump_K.wav (listen to what actually arrives)."""
        if not self.app.dump_s:
            return
        self._dump.append(pcm.copy())
        if sum(len(x) for x in self._dump) >= RATE * self.app.dump_s:
            self._dump_n += 1
            fn = "dump_%d.wav" % self._dump_n
            with wave.open(fn, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(RATE)
                w.writeframes(np.concatenate(self._dump).tobytes())
            log.info("[%s] saved %s (%d s)", self.name, fn, self.app.dump_s)
            self._dump = []

    # ---------------------------------------------------------- state
    def _reset_listen(self):
        self.rec = []
        self.rec_ms = 0
        self.silence_ms = 0
        self.speech_started = False

    def _reset_wake(self):
        self.app.wake.reset()
        self.wake_buf = np.zeros(0, dtype=np.int16)

    async def set_state(self, state):
        self.state = state
        log.info("[%s] state -> %s", self.name, state)
        await self.send_json({"type": "state", "state": state})

    async def send_json(self, obj):
        await self.ws.send(json.dumps(obj))

    # ---------------------------------------------------------- input
    async def run(self):
        async for message in self.ws:
            if isinstance(message, bytes):
                await self.on_audio(message)
            else:
                await self.on_text(message)
        if self._job:
            self._job.cancel()

    async def on_text(self, text):
        try:
            msg = json.loads(text)
        except ValueError:
            return
        t = msg.get("type")
        if t == "hello":
            self.name = msg.get("name", "?")
            self.muted = bool(msg.get("muted"))
            log.info("[%s] hello, rate=%s", self.name, msg.get("rate"))
            await self.send_json({"type": "volume", "value": self.app.volume})
            await self.set_state("idle")
        elif t == "mute":
            self.muted = bool(msg.get("value"))
            log.info("[%s] muted=%s", self.name, self.muted)
            if self.muted and self.state == "listening":
                self._reset_listen()
                await self.set_state("idle")

    async def on_audio(self, data: bytes):
        if self.muted or self.state not in ("idle", "listening", "speaking"):
            return
        valid_len = (len(data) // 2) * 2
        if valid_len == 0:
            return
        pcm = np.frombuffer(data[:valid_len], dtype=np.int16)

        if self.app.meter and len(pcm):
            peak = int(np.max(np.abs(pcm)))
            if peak >= 32000:
                log.warning("[%s] MICROPHONE OVERLOAD (peak=%d)! Increase MIC_SHIFT (less gain) in the firmware.",
                            self.name, peak)

        if self.state == "idle":
            self._dump_audio(pcm)
            await self._on_idle_audio(pcm)
        elif self.state == "listening":
            await self._on_listening_audio(pcm)
        elif self.state == "speaking" and self.app.barge_in:
            await self._on_speaking_audio(pcm)

    # ---------------------------------------------------------- idle: wake word
    async def _on_idle_audio(self, pcm):
        self.wake_buf = np.concatenate([self.wake_buf, pcm])
        while len(self.wake_buf) >= WAKE_FRAME:
            frame, self.wake_buf = self.wake_buf[:WAKE_FRAME], self.wake_buf[WAKE_FRAME:]
            score = self.app.wake.detect(frame)
            if self.app.meter:
                self._meter(pcm, score)
            if score >= self.app.wake.threshold:
                log.info("[%s] wake word! score=%.2f", self.name, score)
                self._reset_wake()
                self._reset_listen()
                await self.set_state("listening")
                return

    def _meter(self, pcm, score):
        self._m_rms = max(self._m_rms, float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2))))
        self._m_score = max(self._m_score, score)
        if time.time() - self._m_t >= 2.0:
            log.info("[%s] audio level (RMS) %.0f, max wake word score %.2f (threshold %.2f)",
                     self.name, self._m_rms, self._m_score, self.app.wake.threshold)
            self._m_t, self._m_rms, self._m_score = time.time(), 0.0, 0.0

    # ---------------------------------------------------------- speaking: barge-in
    async def _on_speaking_audio(self, pcm):
        self.wake_buf = np.concatenate([self.wake_buf, pcm])
        while len(self.wake_buf) >= WAKE_FRAME:
            frame, self.wake_buf = self.wake_buf[:WAKE_FRAME], self.wake_buf[WAKE_FRAME:]
            score = self.app.wake.detect(frame)
            if score >= self.app.barge_threshold:
                log.info("[%s] interrupted by the wake word! score=%.2f", self.name, score)
                await self._barge_in()
                return

    async def _barge_in(self):
        """Aborts the answer and starts listening for a new phrase."""
        self._interrupted = True                # _process must not switch the state to idle
        if self._job:
            self._job.cancel()
            self._job = None
        self._reset_wake()
        self._reset_listen()
        self._deaf_until = time.monotonic() + BARGE_DEAF_S
        await self.send_json({"type": "stop"})  # the speaker flushes its playback buffer
        await self.set_state("listening")

    # ---------------------------------------------------------- listening: record until silence
    async def _on_listening_audio(self, pcm):
        if time.monotonic() < self._deaf_until:
            return
        dur = len(pcm) * 1000 // RATE
        rms = float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2))) if len(pcm) else 0.0
        self.rec.append(pcm)
        self.rec_ms += dur
        if rms >= self.app.vad_rms:
            self.speech_started = True
            self.silence_ms = 0
        else:
            self.silence_ms += dur

        done = self.speech_started and self.silence_ms >= self.app.end_silence_ms
        too_long = self.rec_ms >= self.app.max_listen_ms
        no_speech = (not self.speech_started) and self.rec_ms >= self.app.no_speech_ms

        if no_speech:
            log.info("[%s] nobody said anything", self.name)
            self._reset_listen()
            await self.set_state("idle")
        elif done or too_long:
            audio = np.concatenate(self.rec)
            self._reset_listen()
            await self.set_state("thinking")
            self._job = asyncio.create_task(self._process(audio))

    # ---------------------------------------------------------- thinking -> speaking
    async def _process(self, audio: np.ndarray):
        loop = asyncio.get_running_loop()
        try:
            t0 = time.time()
            text, lang = await loop.run_in_executor(None, self.app.stt.transcribe, audio)
            log.info("[%s] STT (%.1fs) [%s]: %r", self.name, time.time() - t0, lang, text)
            reply = await loop.run_in_executor(None, brain.respond, text, lang) if text else None
            if reply and reply.text:
                log.info("[%s] reply [%s]: %r", self.name, reply.lang, reply.text)
                pcm = await loop.run_in_executor(None, self.app.tts.synthesize, reply.text, reply.lang)
                await self.speak(pcm)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("[%s] processing error", self.name)
            await self.send_json({"type": "state", "state": "error"})
            await asyncio.sleep(0.8)
        finally:
            if self._interrupted:               # interrupted: the state is already "listening"
                self._interrupted = False
            else:
                self._reset_wake()
                try:
                    await self.set_state("idle")
                except websockets.ConnectionClosed:
                    pass

    async def speak(self, pcm: np.ndarray):
        """Streams audio in real time (with a small lead) so that `stop` reaches the speaker
        quickly instead of waiting in the queue behind the audio."""
        self._reset_wake()                      # do not catch the wake word from our own tail
        await self.set_state("speaking")
        data = pcm.astype("<i2").tobytes()
        t0 = time.monotonic()
        sent_s = 0.0
        for i in range(0, len(data), SEND_CHUNK):
            ahead = sent_s - (time.monotonic() - t0)
            if ahead > SPEAK_LEAD_S:
                await asyncio.sleep(ahead - SPEAK_LEAD_S)
            chunk = data[i:i + SEND_CHUNK]
            await self.ws.send(chunk)
            sent_s += len(chunk) / 2 / RATE
        await self.send_json({"type": "audio_end"})
        # wait until the speaker finishes playing (barge-in still works meanwhile)
        await asyncio.sleep(max(0.0, sent_s - (time.monotonic() - t0)) + 0.5)
