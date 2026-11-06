"""ESP32-S3 smart speaker (MicroPython). Assembly and startup only.

New feature: create a module with `async def task()` and add it to TASKS.
New server command: @link.handler("type") (see link.py).
"""
import asyncio

import machine

import audio
import config
import controls
import led
import link
import supervisor

TASKS = (
    led.task,
    audio.mic_task,
    audio.send_task,
    audio.play_task,
    controls.task,
    link.task,
    supervisor.task,
)


async def main():
    audio.init()
    await asyncio.gather(*(asyncio.create_task(t()) for t in TASKS))


try:
    asyncio.run(main())
except KeyboardInterrupt:
    raise                                   # Ctrl+C in the REPL: do not reboot
except Exception as e:
    import sys
    sys.print_exception(e)
    import time
    time.sleep(config.CRASH_RESET_DELAY_S)
    machine.reset()                         # fatal task error -> reboot
