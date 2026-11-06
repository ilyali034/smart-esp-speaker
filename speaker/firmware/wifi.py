"""Wi-Fi: suspends the calling task until connected."""
import asyncio
import network

import secrets


async def ensure():
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        return sta
    sta.active(True)
    sta.config(pm=network.WLAN.PM_NONE)     # no power saving: steadier stream
    while not sta.isconnected():
        print("wifi: connecting to", secrets.WIFI_SSID)
        try:
            sta.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
        except OSError as e:
            print("wifi error:", e)
        for _ in range(40):
            if sta.isconnected():
                break
            await asyncio.sleep_ms(250)
        else:
            sta.disconnect()
            await asyncio.sleep(2)
    print("wifi: ok", sta.ifconfig())
    return sta
