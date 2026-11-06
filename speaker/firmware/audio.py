"""Microphone (INMP441) -> queue -> server; server -> queue -> speaker (MAX98357A)."""
import asyncio
import time

from machine import I2S, Pin

import config
from audio_utils import mic32_to_pcm16, scale_pcm16
from state import st, SPEAKING

_mic_reader = None
_i2s_out = None
_spk_writer = None
_send_q = []            # microphone -> server
_play_q = []            # server -> speaker
_flush = False          # request to flush the speaker buffer (barge-in)


def _make_speaker():
    """(Re)creates the I2S output: this is how the hardware buffer is flushed on stop."""
    global _i2s_out, _spk_writer
    if _i2s_out is not None:
        try:
            _i2s_out.deinit()
        except Exception:
            pass
    _i2s_out = I2S(
        1, sck=Pin(config.SPK_BCLK), ws=Pin(config.SPK_LRC), sd=Pin(config.SPK_DIN),
        mode=I2S.TX, bits=16, format=I2S.MONO,
        rate=config.SAMPLE_RATE, ibuf=config.SPK_IBUF)
    _spk_writer = asyncio.StreamWriter(_i2s_out)


def init():
    """Call once from main before starting the tasks."""
    global _mic_reader
    i2s_in = I2S(
        0, sck=Pin(config.MIC_SCK), ws=Pin(config.MIC_WS), sd=Pin(config.MIC_SD),
        mode=I2S.RX, bits=32, format=I2S.MONO,
        rate=config.SAMPLE_RATE, ibuf=config.MIC_IBUF)
    _mic_reader = asyncio.StreamReader(i2s_in)
    _make_speaker()


# ---------------------------------------------------------------- microphone
async def _read_full(buf):
    """readinto may return fewer bytes (or None) - keep reading until len(buf) bytes are in."""
    mv = memoryview(buf)
    n, total = 0, len(buf)
    while n < total:
        k = await _mic_reader.readinto(mv[n:])
        if k:
            n += k


async def mic_task():
    """Reads the mic non-stop (otherwise the DMA overflows). Sending is done by send_task."""
    raw = bytearray(config.CHUNK * 4)
    pcm = bytearray(config.CHUNK * 2)
    peak_max, t_dbg = 0, time.ticks_ms()
    while True:
        try:
            await _read_full(raw)
        except Exception as e:
            print("mic read error:", e)
            await asyncio.sleep_ms(50)
            continue
        peak = mic32_to_pcm16(raw, pcm, config.CHUNK, config.MIC_SHIFT)
        if config.DEBUG_MIC:
            peak_max = max(peak_max, peak)
            if time.ticks_diff(time.ticks_ms(), t_dbg) > 2000:
                print("mic peak:", peak_max, "| muted" if st.muted else "", "|", st.mode)
                peak_max, t_dbg = 0, time.ticks_ms()
        silent = st.mode == SPEAKING and not config.BARGE_IN
        if st.ws is None or st.muted or silent:
            del _send_q[:]
            continue
        if len(_send_q) >= config.SEND_Q_MAX:
            _send_q.pop(0)              # network is slow: drop the oldest
        _send_q.append(bytes(pcm))      # copy: pcm is overwritten by the next read


async def send_task():
    while True:
        ws = st.ws
        if ws is None or not _send_q:
            await asyncio.sleep_ms(5)
            continue
        try:
            await ws.send_bytes(_send_q.pop(0))
        except Exception as e:
            print("mic send error:", e)
            st.ws = None                # connection task will reconnect


# ---------------------------------------------------------------- speaker
async def enqueue(chunk):
    """Queues a packet for playback. Does not block message handling while there is room."""
    st.last_audio_ms = time.ticks_ms()
    while len(_play_q) >= config.PLAY_Q_MAX:
        await asyncio.sleep_ms(10)
    _play_q.append(chunk)


def stop():
    """Abort playback: the queue is emptied, the hardware buffer is flushed by play_task."""
    global _flush
    del _play_q[:]
    _flush = True


async def play_task():
    global _flush
    while True:
        if _flush:
            _flush = False
            _make_speaker()
        if not _play_q:
            await asyncio.sleep_ms(5)
            continue
        chunk = _play_q.pop(0)
        n = len(chunk) // 2
        if n == 0:
            continue
        buf = bytearray(chunk[: n * 2])
        scale_pcm16(buf, n, st.volume_q8)
        st.last_audio_ms = time.ticks_ms()
        await _spk_writer.awrite(buf)
