# Smart ESP Speaker

Bilingual (English + Russian) smart speaker: an ESP32-S3 (microphone + speaker) talks to a PC server
that does wake word detection, speech recognition, answer generation and speech synthesis.

```
ESP32 --PCM16 16 kHz--> server: WakeWord -> VAD -> Whisper (en/ru auto) -> Brain -> Piper (en/ru voice)
ESP32 <--PCM16 16 kHz-- server
```

## Layout
| Path | What |
|---|---|
| `firmware/` | MicroPython for the ESP32-S3 |
| `server/speaker_server/` | Python server package |
| `server/speaker_server/brain/` | answer logic: local commands, Ollama, web lookup (en/ru) |
| `server/speaker_server/engines/` | STT (faster-whisper), TTS (Piper) |
| `docs/PROTOCOL.md` | ESP <-> server protocol |
| `docs/DEVELOPING.md` | how to add features / languages |
| `tests/` | unit tests (no hardware or models needed) |

## Run the server
```
cd server
python -m venv .venv && .venv\Scripts\activate     # Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m speaker_server --device cuda --compute-type float16 ^
    --piper-model en=C:\voices\en_US-lessac-medium.onnx ^
    --piper-model ru=C:\voices\ru_RU-irina-medium.onnx --meter
```
The server prints `ws://IP:8765` - put that address into `firmware/secrets.py`.

Languages: `--languages en,ru` (default). The spoken language is detected per phrase by Whisper
(restricted to the listed languages), and the reply is spoken with the voice of the same language.
Use `--whisper-model medium` if short phrases get detected wrongly.

Wake word: openWakeWord ships English models (`hey_jarvis`, `alexa`, ...). They are used for both
languages. Custom `.onnx` wake words are supported via `--wake-word path.onnx`.

## Flash the firmware
```
cd firmware
copy secrets_example.py secrets.py      # fill in
mpremote cp *.py :
```

## Tests
```
python -m unittest discover -s tests -v
```
