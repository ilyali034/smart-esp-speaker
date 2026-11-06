import json
import urllib.request

WEB_TIMEOUT = 5


def get_json(url, timeout=WEB_TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": "smart-esp-speaker/1.0 (home project)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def post_json(url, payload, timeout):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))
