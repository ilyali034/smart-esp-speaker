"""Minimal WebSocket client (RFC 6455) on top of uasyncio for MicroPython.

Supports: ws:// (no TLS), text and binary frames, ping/pong, close, fragmentation.
Outgoing frames use an all-zero mask: RFC 6455 allows any 4-byte masking key, and on a local
network this saves CPU (no per-byte XOR).
"""
import asyncio
import binascii
import os
import struct

OP_CONT = 0x0
OP_TEXT = 0x1
OP_BIN = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

_ZERO_MASK = b"\x00\x00\x00\x00"


class WSClosed(Exception):
    pass


class WebSocket:
    def __init__(self, reader, writer):
        self._r = reader
        self._w = writer
        self.closed = False

    @classmethod
    async def connect(cls, host, port, path="/", timeout=8):
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
        key = binascii.b2a_base64(os.urandom(16)).strip().decode()
        req = (
            "GET {} HTTP/1.1\r\n"
            "Host: {}:{}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: {}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).format(path, host, port, key)
        writer.write(req.encode())
        await writer.drain()

        status = await asyncio.wait_for(reader.readline(), timeout)
        if b" 101 " not in status:
            writer.close()
            raise OSError("handshake failed: " + status.decode().strip())
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout)
            if line in (b"\r\n", b"\n", b""):
                break
        return cls(reader, writer)

    async def _send(self, opcode, payload):
        n = len(payload)
        if n < 126:
            head = struct.pack("BB", 0x80 | opcode, 0x80 | n)
        elif n < 65536:
            head = struct.pack(">BBH", 0x80 | opcode, 0x80 | 126, n)
        else:
            head = struct.pack(">BBQ", 0x80 | opcode, 0x80 | 127, n)
        # one write() per frame: frames from different tasks do not interleave
        self._w.write(head + _ZERO_MASK + payload)
        await self._w.drain()

    async def send_text(self, text):
        await self._send(OP_TEXT, text.encode())

    async def send_bytes(self, data):
        await self._send(OP_BIN, data)

    async def _readexactly(self, n):
        return await self._r.readexactly(n)

    async def recv(self):
        """Returns (opcode, payload) of a whole message (TEXT or BIN)."""
        msg_op = None
        msg = b""
        while True:
            b1, b2 = await self._readexactly(2)
            fin = b1 & 0x80
            op = b1 & 0x0F
            masked = b2 & 0x80
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", await self._readexactly(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", await self._readexactly(8))[0]
            mask = await self._readexactly(4) if masked else None
            payload = await self._readexactly(n) if n else b""
            if mask:
                payload = bytes(c ^ mask[i & 3] for i, c in enumerate(payload))

            if op == OP_PING:
                await self._send(OP_PONG, payload)
                continue
            if op == OP_PONG:
                continue
            if op == OP_CLOSE:
                self.closed = True
                try:
                    await self._send(OP_CLOSE, payload[:2])
                except Exception:
                    pass
                raise WSClosed()

            if op != OP_CONT:
                msg_op = op
                msg = payload
            else:
                msg += payload
            if fin:
                return msg_op, msg

    def close(self):
        self.closed = True
        try:
            self._w.close()
        except Exception:
            pass
