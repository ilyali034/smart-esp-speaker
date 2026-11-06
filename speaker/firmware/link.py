"""Server link: connect, reconnect, protocol.

New command from the server:
    @handler("my_type")
    async def _(msg): ...
"""
import asyncio
import gc
import json

import audio
import config
import secrets
import wifi
from state import st, IDLE
from ws import WebSocket, WSClosed, OP_TEXT, OP_BIN

_handlers = {}


def handler(msg_type):
    def deco(fn):
        _handlers[msg_type] = fn
        return fn
    return deco


async def send_json(obj):
    """Safe JSON send to the server (silently ignored when there is no connection)."""
    ws = st.ws
    if ws is None:
        return False
    try:
        await ws.send_text(json.dumps(obj))
        return True
    except Exception as e:
        print("send_json error:", e)
        return False


# ---------------------------------------------------------------- server commands
@handler("state")
async def _on_state(msg):
    st.mode = msg.get("state", IDLE)


@handler("volume")
async def _on_volume(msg):
    v = float(msg.get("value", 1.0))                # 0.0 .. 4.0
    st.volume_q8 = max(0, min(1024, int(v * 256)))


@handler("mute")
async def _on_mute(msg):
    st.muted = bool(msg.get("value"))


@handler("stop")
async def _on_stop(msg):
    audio.stop()                                    # interrupted: flush the speaker buffer


@handler("audio_end")
async def _on_audio_end(msg):
    pass


@handler("ping")
async def _on_ping(msg):
    await send_json({"type": "pong"})


# ---------------------------------------------------------------- session
async def _dispatch(payload):
    try:
        msg = json.loads(payload.decode())
    except ValueError:
        return
    fn = _handlers.get(msg.get("type"))
    if fn is None:
        print("link: unknown command:", msg.get("type"))
        return
    try:
        await fn(msg)
    except Exception as e:
        print("link: handler error:", repr(e))


async def _session():
    print("server: connecting to ws://%s:%d%s" % (secrets.SERVER_HOST, secrets.SERVER_PORT, config.SERVER_PATH))
    ws = await WebSocket.connect(secrets.SERVER_HOST, secrets.SERVER_PORT, config.SERVER_PATH)
    try:
        await ws.send_text(json.dumps({
            "type": "hello", "name": config.DEVICE_NAME,
            "rate": config.SAMPLE_RATE, "muted": st.muted}))
        st.ws, st.connected, st.mode = ws, True, IDLE
        print("server: connected")
        while True:
            op, payload = await ws.recv()
            if op == OP_BIN:
                await audio.enqueue(payload)
            elif op == OP_TEXT:
                await _dispatch(payload)
    finally:
        st.connected, st.ws, st.mode = False, None, IDLE
        ws.close()
        print("server: disconnected")


async def task():
    backoff = 1
    while True:
        await wifi.ensure()
        try:
            await _session()
            backoff = 1
        except (WSClosed, OSError, EOFError, asyncio.TimeoutError) as e:
            print("server: disconnected:", repr(e))
        except Exception as e:
            print("server: error:", repr(e))
        gc.collect()
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, config.RECONNECT_MAX_S)
