#!/usr/bin/env python3
"""Minimal TopSMS delivery-report webhook receiver (standard library only, Python 3.8+).

  export TOPSMS_WEBHOOK_SECRET=...   # shown once when you set the webhook URL on the API key
  python3 webhook_receiver.py 8080

Verifies X-TopSMS-Signature: sha256=hex(HMAC-SHA256(secret, raw body)) and prints the event.
Put it behind HTTPS (reverse proxy) and register the final public URL on the API key.
"""
import hashlib
import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

SECRET = os.environ.get("TOPSMS_WEBHOOK_SECRET", "").encode("utf-8")
seen = set()  # use your database in production


def valid_signature(raw: bytes, header: str) -> bool:
    if not SECRET or not header.startswith("sha256="):
        return False
    expected = hmac.new(SECRET, raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[len("sha256="):])


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))  # raw bytes, before any JSON parsing
        if not valid_signature(raw, self.headers.get("X-TopSMS-Signature", "")):
            self.send_response(401)
            self.end_headers()
            return
        event = json.loads(raw)
        key = (event.get("id"), event.get("status"))
        if key not in seen:  # idempotent: the same event can arrive again after a timeout
            seen.add(key)
            print(f"{event.get('status'):>9} {event.get('to')} id={event.get('id')} "
                  f"errorCode={event.get('errorCode')} test={event.get('test', False)}", flush=True)
        self.send_response(204)  # any 2xx within 5 s
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    if not SECRET:
        sys.exit("Set TOPSMS_WEBHOOK_SECRET")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"listening on :{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
