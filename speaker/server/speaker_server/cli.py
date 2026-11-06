import argparse
import os


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Smart speaker server")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--wake-word", default=os.environ.get("WAKE_WORD", "hey_jarvis"),
                   help="hey_jarvis, alexa, hey_mycroft, hey_rhasspy or a path to your own .onnx")
    p.add_argument("--wake-threshold", type=float, default=0.5)
    p.add_argument("--whisper-model", default="small", help="tiny/base/small/medium/large-v3 (not the *.en models)")
    p.add_argument("--languages", default=os.environ.get("LANGUAGES", "en,ru"),
                   help="comma-separated recognition languages; detected per phrase among these (default: en,ru)")
    p.add_argument("--device", default="cpu", help="cpu or cuda")
    p.add_argument("--compute-type", default="int8", help="int8, or float16 (for cuda)")
    p.add_argument("--piper-model", action="append", default=None, metavar="LANG=PATH",
                   help="Piper voice per language, repeatable: --piper-model en=a.onnx --piper-model ru=b.onnx "
                        "(a .onnx.json must sit next to each). Env: PIPER_MODEL_EN, PIPER_MODEL_RU")
    p.add_argument("--piper-bin", default="piper")
    p.add_argument("--vad-rms", type=float, default=450.0,
                   help="speech loudness threshold (int16 RMS); raise it in a noisy room")
    p.add_argument("--end-silence-ms", type=int, default=900)
    p.add_argument("--max-listen-ms", type=int, default=12000)
    p.add_argument("--no-speech-ms", type=int, default=5000)
    p.add_argument("--volume", type=float, default=1.0, help="speaker volume 0..4")
    p.add_argument("--no-barge-in", action="store_true",
                   help="disable interrupting the answer with the wake word")
    p.add_argument("--barge-threshold", type=float, default=0.6,
                   help="wake word threshold while speaking (higher than normal: speaker echo)")
    p.add_argument("--dump-wav", type=int, default=0, metavar="SEC",
                   help="save every N seconds of speaker audio to dump_K.wav (microphone diagnostics)")
    p.add_argument("--meter", action="store_true",
                   help="log audio level and wake word score every 2 s")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    args.languages = tuple(l.strip().lower() for l in args.languages.split(",") if l.strip()) or ("en",)
    return args
