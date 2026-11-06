"""Shared audio constants and helpers."""
import numpy as np

RATE = 16000


def resample(pcm16: np.ndarray, src_rate: int, dst_rate: int = RATE) -> np.ndarray:
    if src_rate == dst_rate or len(pcm16) == 0:
        return pcm16
    n_out = int(len(pcm16) * dst_rate / src_rate)
    x_old = np.linspace(0.0, 1.0, num=len(pcm16), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
    out = np.interp(x_new, x_old, pcm16.astype(np.float32))
    return np.clip(out, -32768, 32767).astype(np.int16)


def beep(freq=880.0, ms=250) -> np.ndarray:
    t = np.arange(int(RATE * ms / 1000)) / RATE
    fade = np.minimum(1.0, np.minimum(t, t[-1] - t) * 40)
    return (np.sin(2 * np.pi * freq * t) * fade * 12000).astype(np.int16)
