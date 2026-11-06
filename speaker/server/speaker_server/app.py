"""Server assembly: models + WebSocket."""
import asyncio
import logging

import websockets

from .engines import STT, TTS
from .net import get_local_ips
from .session import Session
from .voices import collect_voice_specs
from .wake import WakeWord

log = logging.getLogger("server")


class App:
    """Shared resources available to every session."""

    def __init__(self, wake, stt, tts, args):
        self.wake = wake
        self.stt = stt
        self.tts = tts
        self.vad_rms = args.vad_rms
        self.end_silence_ms = args.end_silence_ms
        self.max_listen_ms = args.max_listen_ms
        self.no_speech_ms = args.no_speech_ms
        self.volume = args.volume
        self.meter = args.meter
        self.barge_in = not args.no_barge_in
        self.barge_threshold = args.barge_threshold
        self.dump_s = args.dump_wav


async def handler(ws, app):
    peer = getattr(ws, "remote_address", "unknown")
    log.info("speaker connected: %s", peer)
    try:
        await Session(ws, app).run()
    except websockets.ConnectionClosed:
        log.info("speaker %s: connection closed", peer)
    except Exception as e:
        log.error("session error %s: %s", peer, e)
    finally:
        log.info("speaker disconnected: %s", peer)


async def amain(args):
    log.info("loading models...")
    tts = TTS(collect_voice_specs(args.piper_model), args.piper_bin)
    for lang in args.languages:
        if not tts.has_voice(lang):
            log.warning("no Piper voice for %r: replies in this language will be a beep "
                        "(add --piper-model %s=PATH)", lang, lang)
    app = App(
        WakeWord(args.wake_word, args.wake_threshold),
        STT(args.whisper_model, args.languages, args.device, args.compute_type),
        tts,
        args,
    )
    async with websockets.serve(
        lambda ws: handler(ws, app), args.host, args.port,
        max_size=2 ** 20, ping_interval=20, ping_timeout=10,   # keepalive: routers drop idle connections
    ):
        log.info("=" * 65)
        log.info("SERVER READY. PUT ONE OF THESE ADDRESSES INTO firmware/secrets.py:")
        for ip in get_local_ips():
            log.info("  >>>  ws://%s:%d", ip, args.port)
        log.info("=" * 65)
        await asyncio.Future()
