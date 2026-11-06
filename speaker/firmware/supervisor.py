"""Safety nets: leave a stuck SPEAKING state, run gc, feed the hardware watchdog."""
import asyncio
import gc
import time

import config
from state import st, IDLE, SPEAKING


async def task():
    wdt = None
    if config.WDT_TIMEOUT_MS:
        from machine import WDT
        wdt = WDT(timeout=config.WDT_TIMEOUT_MS)
    while True:
        if st.mode == SPEAKING and time.ticks_diff(time.ticks_ms(), st.last_audio_ms) > config.SPEAKING_TIMEOUT_MS:
            print("supervisor: speaking timeout")
            st.mode = IDLE
        gc.collect()
        if wdt:
            wdt.feed()
        await asyncio.sleep(2)
