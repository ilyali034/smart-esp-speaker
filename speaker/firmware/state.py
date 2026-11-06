"""Single shared state. Import `st`; do not keep globals in modules."""
import config

IDLE, LISTENING, THINKING, SPEAKING = "idle", "listening", "thinking", "speaking"


class State:
    def __init__(self):
        self.mode = IDLE                    # state reported by the server
        self.muted = False
        self.connected = False
        self.ws = None                      # active WebSocket or None
        self.volume_q8 = config.VOLUME_Q8
        self.last_audio_ms = 0              # last time audio was played


st = State()
