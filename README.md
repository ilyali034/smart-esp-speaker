# Speaker firmware (ESP32-S3, MicroPython)

| File | Role |
|---|---|
| main.py | task list, startup, reset on fatal error |
| config.py | hardware, timings |
| secrets.py | Wi-Fi, server address (git-ignored) |
| state.py | shared state `st` |
| link.py | WebSocket session, command registry `@handler` |
| audio.py | microphone, speaker, send/play queues |
| led.py / controls.py / supervisor.py | LED / button / watchdog |
| ws.py, audio_utils.py | WebSocket client, viper converters |

Flash: copy every `.py` to the flash root (`mpremote cp *.py :`), including `secrets.py`.

## Add a feature
1. Create `feature.py` with `async def task()`.
2. Add it to `TASKS` in main.py.
3. Server command: `@link.handler("name")` + `async def _(msg)`.
4. Event to the server: `await link.send_json({...})`.
5. Shared data: add a field to `State` (state.py).
