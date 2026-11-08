#!/usr/bin/env python3
"""Interactive TopSMS Verify API demo: send a code, then check what you type.

  export TOPSMS_CLIENT_ID=...  TOPSMS_SECRET=...   # a TEST key prints testCode, nothing is sent
  python3 otp_demo.py +4915112345678 en

Standard library only, Python 3.8+. In production keep the verification id server-side and never log codes.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("TOPSMS_BASE_URL", "https://www.topsms.cz").rstrip("/")


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {os.environ['TOPSMS_CLIENT_ID']}:{os.environ['TOPSMS_SECRET']}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        err = json.loads(e.read() or b"{}")
        raise SystemExit(f"TopSMS {e.code} {err.get('code', '')}: {err.get('error')}")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    to = sys.argv[1]
    locale = sys.argv[2] if len(sys.argv) > 2 else "en"
    sent = post("/api/verify/send", {"to": to, "brand": "Demo", "locale": locale, "length": 6, "ttl": 300})
    print(f"code sent, verification id {sent['id']}, expires {sent['expiresAt']}")
    if sent.get("test"):
        print(f"test key: the code is {sent['testCode']}")  # only test keys return the code
    while True:
        code = input("code: ").strip()
        res = post("/api/verify/check", {"id": sent["id"], "code": code})
        if res["valid"]:
            print("verified")
            return
        if res["status"] != "pending":
            print(f"not verified: {res['status']}")
            return
        print(f"wrong code, {res.get('attemptsLeft')} attempts left")


if __name__ == "__main__":
    main()
