# ESP <-> server protocol

WebSocket `ws://host:8765/`. Binary frames = audio, PCM16 little-endian, 16 kHz, mono.
Text frames = JSON `{"type": ...}`.

## ESP -> server
| type / frame | fields | meaning |
|---|---|---|
| binary | PCM16 | microphone audio (not sent while muted) |
| `hello` | name, rate, muted | first message after connecting |
| `mute` | value: bool | BOOT button |
| `pong` | - | reply to `ping` |

The microphone is also streamed while `speaking` (if `BARGE_IN = True`): the server looks for
the wake word and interrupts the answer.

## server -> ESP
| type / frame | fields | meaning |
|---|---|---|
| binary | PCM16 | spoken answer, 4096-byte chunks |
| `state` | state: idle/listening/thinking/speaking/error | LED, mute logic |
| `volume` | value: 0..4 | speaker volume |
| `mute` | value: bool | force mute |
| `stop` | - | answer interrupted: flush playback queue and speaker buffer |
| `audio_end` | - | answer finished (all audio already sent) |
| `ping` | - | firmware replies `pong` |

## Server states
`idle` (wake word search) -> `listening` (record until silence) -> `thinking` (STT + brain + TTS)
-> `speaking` -> `idle`.

Barge-in: wake word during `speaking` -> `stop` + `state: listening`.
The server streams answer audio in real time (0.4 s lead), otherwise `stop` would sit in the TCP
queue behind the audio.

## Languages
Language handling is server-side only; the protocol carries no language field.

## Adding a message
1. Describe it here.
2. Server: `Session.on_text` in `server/speaker_server/session.py`.
3. Firmware: `@link.handler("type")` in `firmware/link.py`.
