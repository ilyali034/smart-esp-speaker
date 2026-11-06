# Development

## New local voice command (no LLM)
`server/speaker_server/brain/local.py` - register one command per language:
```python
@command("en", r"turn on the light")
def _light_en(match, text):
    return "Turning on the light"

@command("ru", r"включи\s+свет")
def _light_ru(match, text):
    return "Включаю свет"
```
A command returns a string to speak (`""` = stay silent) or `None` (did not handle it).
Commands of the detected language are tried first, then the others; the language of the
matched command decides the TTS voice. Declaration order = priority.

## New language (e.g. German)
1. `--languages en,ru,de`; add a Piper voice: `--piper-model de=path.onnx`.
2. `brain/i18n.py`: add `de` entries (system prompt, not-found message).
3. `brain/web.py`: add a topic regex for `de`.
4. `brain/local.py`: add `@command("de", ...)` commands.

## Another answer source
Add a module in `brain/` with `ask(text, lang) -> str`, hook it into `brain/__init__.py::respond`.

## Another STT / TTS engine
`engines/stt.py`: `transcribe(pcm16) -> (text, lang)`.
`engines/tts.py`: `synthesize(text, lang) -> pcm16 16 kHz mono`.

## New firmware feature
See `firmware/README.md`.

## Rules
- Hardware-free logic goes in `brain/` and is covered by `tests/`.
- Settings are CLI arguments / environment variables, not constants in code.
- Never commit secrets (`firmware/secrets.py`, `.env`).
- New protocol messages: update `docs/PROTOCOL.md` first.
