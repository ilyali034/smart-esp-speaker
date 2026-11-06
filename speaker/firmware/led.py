"""Status LED. Red = muted, blinking orange = no connection, dim blue = waiting for the wake word,
cyan = listening, yellow = thinking, green = speaking."""
import asyncio
import math
import time

import neopixel
from machine import Pin

import config
from state import st, LISTENING, THINKING, SPEAKING

_np = neopixel.NeoPixel(Pin(config.LED_PIN), 1)


def set_led(r, g, b):
    k = config.LED_BRIGHTNESS
    _np[0] = (r * k // 255, g * k // 255, b * k // 255)
    _np.write()


async def task():
    while True:
        t = time.ticks_ms()
        pulse = 0.5 + 0.5 * math.sin(t / 250)
        if st.muted:
            set_led(255, 0, 0)
        elif not st.connected:
            on = (t // 500) % 2
            set_led(255 if on else 0, 80 if on else 0, 0)
        elif st.mode == LISTENING:
            set_led(0, int(120 + 135 * pulse), 255)
        elif st.mode == THINKING:
            set_led(int(120 + 135 * pulse), int(90 + 100 * pulse), 0)
        elif st.mode == SPEAKING:
            set_led(0, 255, 40)
        else:
            set_led(0, 0, 40)
        await asyncio.sleep_ms(40)
