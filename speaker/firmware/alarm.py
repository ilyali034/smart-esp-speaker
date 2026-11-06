"""Persistent one-shot alarm: scheduled and rung locally on the ESP32."""
import asyncio
import json
import math
import time

import audio
import link
from state import st

_ALARM_FILE = "alarm.json"
_alarm_at = None                 # (year, month, day, hour, minute), local RTC time


def _read_alarm():
    try:
        with open(_ALARM_FILE, "r") as f:
            value = json.load(f)
        if len(value) != 5:
            return None
        return tuple(int(part) for part in value)
    except Exception:
        return None


def _save_alarm(value):
    try:
        if value is None:
            import os
            try:
                os.remove(_ALARM_FILE)
            except OSError:
                pass
        else:
            with open(_ALARM_FILE, "w") as f:
                json.dump(list(value), f)
    except Exception as e:
        print("alarm: could not persist schedule:", repr(e))


def _ring_tone():
    """A short two-pulse, 880 Hz ringtone; generated once without extra packages."""
    rate = 16000
    count = int(rate * 0.48)
    tone = bytearray(count * 2)
    for i in range(count):
        t = i / rate
        active = t < 0.18 or 0.27 <= t < 0.45
        sample = int(math.sin(2 * math.pi * 880 * t) * 7500) if active else 0
        tone[2 * i] = sample & 255
        tone[2 * i + 1] = (sample >> 8) & 255
    return bytes(tone)


_TONE = _ring_tone()


def _set_schedule(msg):
    global _alarm_at
    try:
        year, month, day = int(msg["year"]), int(msg["month"]), int(msg["day"])
        hour, minute = int(msg["hour"]), int(msg["minute"])
        if not (2020 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31
                and 0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("out of range")
        _alarm_at = (year, month, day, hour, minute)
        st.alarm_ringing = False
        st.alarm_beep = False
        audio.stop()
        _save_alarm(_alarm_at)
        print("alarm: set for", _alarm_at)
    except (KeyError, TypeError, ValueError) as e:
        print("alarm: invalid schedule:", repr(e))


@link.handler("clock")
async def _on_clock(msg):
    try:
        from machine import RTC
        year, month, day, weekday, hour, minute, second = msg["datetime"]
        RTC().datetime((int(year), int(month), int(day), int(weekday),
                        int(hour), int(minute), int(second), 0))
    except Exception as e:
        print("alarm: clock sync failed:", repr(e))


@link.handler("alarm_set")
async def _on_alarm_set(msg):
    _set_schedule(msg)


@link.handler("alarm_stop")
async def _on_alarm_stop(msg):
    global _alarm_at
    st.alarm_ringing = False
    st.alarm_beep = False
    _alarm_at = None
    _save_alarm(None)
    audio.stop()
    print("alarm: stopped")


async def task():
    global _alarm_at
    _alarm_at = _read_alarm()
    last_notified_ws = None
    while True:
        if st.alarm_ringing:
            if st.ws is not None and st.ws is not last_notified_ws:
                if await link.send_json({"type": "alarm_ringing"}):
                    last_notified_ws = st.ws
            st.alarm_beep = True
            await audio.enqueue(_TONE)
            await asyncio.sleep_ms(550)
            st.alarm_beep = False
            await asyncio.sleep_ms(1800)
            continue

        last_notified_ws = None
        if _alarm_at is not None:
            now = time.localtime()
            if tuple(now[:5]) >= _alarm_at:
                # Keep the due time on flash until the user dismisses the ring;
                # a reboot during ringing therefore resumes the alarm.
                _alarm_at = None
                st.alarm_ringing = True
                audio.stop()
                print("alarm: ringing")
                continue
        await asyncio.sleep_ms(200)