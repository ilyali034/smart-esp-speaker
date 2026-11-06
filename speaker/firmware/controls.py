"""Physical buttons. BOOT = mute."""
import asyncio

from machine import Pin

import config
import link
from state import st


async def task():
    btn = Pin(config.MUTE_BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    prev = 1
    while True:
        cur = btn.value()
        if prev == 1 and cur == 0:
            st.muted = not st.muted
            print("mute:", st.muted)
            await link.send_json({"type": "mute", "value": st.muted})
            await asyncio.sleep_ms(250)     # debounce
        prev = cur
        await asyncio.sleep_ms(30)
