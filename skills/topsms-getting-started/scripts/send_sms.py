#!/usr/bin/env python3
"""Send one SMS with the TopSMS REST API (standard library only, Python 3.8+).

Usage:
  export TOPSMS_CLIENT_ID=...  TOPSMS_SECRET=...   # use a TEST key while developing
  python3 send_sms.py +4915112345678 "Your order 1024 has shipped."

Prints the JSON response. Exit code 1 on an HTTP error.
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from typing import Optional

BASE = os.environ.get("TOPSMS_BASE_URL", "https://www.topsms.cz").rstrip("/")


def send_sms(to: str, text: str, sender: Optional[str] = None, idempotency_key: Optional[str] = None) -> dict:
    client_id = os.environ["TOPSMS_CLIENT_ID"]
    secret = os.environ["TOPSMS_SECRET"]
    body = {"to": to, "text": text}
    if sender:
        body["from"] = sender
    req = urllib.request.Request(
        BASE + "/api/sms/send",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {client_id}:{secret}",
            "Content-Type": "application/json",
            # same key on a retry = the SMS is never sent twice (valid 24 h)
            "Idempotency-Key": idempotency_key or str(uuid.uuid4()),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        err = json.loads(e.read() or b"{}")
        raise RuntimeError(f"TopSMS {e.code} {err.get('code', '')}: {err.get('error')}") from None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    try:
        print(json.dumps(send_sms(sys.argv[1], sys.argv[2]), indent=2, ensure_ascii=False))
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
