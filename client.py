"""Test client for local + AgentCore invokes. Usage:
   python client.py "prompt text" [optionaldocument.md]
"""
import json, sys, urllib.request
from pathlib import Path

URL = "http://127.0.0.1:8080/invocations"

payload = {"prompt": sys.argv[1] if len(sys.argv) > 1 else "Say READY"}
if len(sys.argv) > 2:
    p = Path(sys.argv[2])
    payload["document"] = {"filename": p.name, "content": p.read_text(encoding="utf-8")}

req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                             headers={"Content-Type": "application/json"})
try:
    print(urllib.request.urlopen(req, timeout=180).read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code} — server error details:")
    print(e.read().decode(errors="replace"))
    sys.exit(1)