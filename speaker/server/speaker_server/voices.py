"""Piper voice configuration: one voice per language. Pure Python (no numpy), unit-tested."""
import os

ANY = "*"        # voice used for every language


def collect_voice_specs(cli_specs=None, environ=None):
    """Build {lang: path}. Sources, later wins: PIPER_MODEL, PIPER_MODEL_<LANG>, --piper-model.

    A CLI spec is "LANG=PATH"; a bare path applies to every language ("*").
    """
    env = os.environ if environ is None else environ
    voices = {}
    if env.get("PIPER_MODEL"):
        voices[ANY] = env["PIPER_MODEL"]
    for key, value in env.items():
        if key.startswith("PIPER_MODEL_") and value:
            voices[key[len("PIPER_MODEL_"):].lower()] = value
    for spec in cli_specs or []:
        if "=" in spec:
            lang, path = spec.split("=", 1)
            voices[lang.strip().lower()] = path.strip()
        else:
            voices[ANY] = spec.strip()
    return voices
