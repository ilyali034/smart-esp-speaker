"""Audio buffer conversion for the ESP32 (MicroPython viper = fast native code)."""
import micropython


@micropython.viper
def mic32_to_pcm16(src, dst, n: int, shift: int) -> int:
    """The INMP441 delivers 24 bits in the upper bits of a 32-bit little-endian word.
    Converts n words from src (4*n bytes) to n PCM16 samples in dst (2*n bytes).
    shift is relative to 32 bits: 16 = no gain, 14 = x4, 12 = x16.
    Returns the peak value (0..32767) for level indication."""
    s = ptr8(src)
    d = ptr8(dst)
    sh = shift - 8                      # shift relative to the 24-bit value
    peak = 0
    for i in range(n):
        j = i * 4
        v = (int(s[j + 3]) << 16) | (int(s[j + 2]) << 8) | int(s[j + 1])
        if v & 0x800000:
            v -= 0x1000000
        v = v >> sh
        if v > 32767:
            v = 32767
        elif v < -32768:
            v = -32768
        a = v if v >= 0 else -v
        if a > peak:
            peak = a
        d[i * 2] = v & 0xFF
        d[i * 2 + 1] = (v >> 8) & 0xFF
    return peak


@micropython.viper
def scale_pcm16(buf, n: int, vol_q8: int):
    """Multiplies n PCM16 samples in buf by vol_q8/256 in place, with clipping."""
    p = ptr8(buf)
    for i in range(n):
        j = i * 2
        v = (int(p[j + 1]) << 8) | int(p[j])
        if v & 0x8000:
            v -= 0x10000
        v = (v * vol_q8) >> 8
        if v > 32767:
            v = 32767
        elif v < -32768:
            v = -32768
        p[j] = v & 0xFF
        p[j + 1] = (v >> 8) & 0xFF
