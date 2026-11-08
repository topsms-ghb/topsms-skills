#!/usr/bin/env python3
"""Send a correctly signed sample TopSMS webhook to your receiver (for local testing).

  export TOPSMS_WEBHOOK_SECRET=...
  python3 sign_test.py http://localhost:8080/
"""
import hashlib
import hmac
import json
import os
import sys
import urllib.request

url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/"
secret = os.environ["TOPSMS_WEBHOOK_SECRET"].encode("utf-8")
body = json.dumps({
    "event": "sms.status", "id": "test_webhook", "externalId": "test-webhook", "to": "+4915112345678",
    "from": "TopSMS", "status": "delivered", "price": 0, "currency": "EUR",
    "deliveredAt": "2026-11-08T09:00:04.000Z", "failedAt": None, "errorMessage": None, "errorCode": None,
    "sentAt": "2026-11-08T09:00:05.000Z", "test": True,
}, separators=(",", ":")).encode("utf-8")
sig = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
req = urllib.request.Request(url, data=body, method="POST", headers={
    "Content-Type": "application/json", "User-Agent": "TopSMS-Webhook/1.1", "X-TopSMS-Signature": sig})
with urllib.request.urlopen(req, timeout=5) as res:
    print("HTTP", res.status)
