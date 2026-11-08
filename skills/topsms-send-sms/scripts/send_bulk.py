#!/usr/bin/env python3
"""Bulk SMS with TopSMS: chunks of 500, deterministic Idempotency-Keys, job polling.

Usage:
  export TOPSMS_CLIENT_ID=...  TOPSMS_SECRET=...   # use a TEST key while developing
  python3 send_bulk.py campaign-2026-12 "Shop closed on Monday." numbers.txt

numbers.txt: one E.164 number per line. The first argument is your batch name; it is
part of each chunk's Idempotency-Key, so running the script twice with the same name
does not send twice (within 24 h).
Standard library only, Python 3.8+.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("TOPSMS_BASE_URL", "https://www.topsms.cz").rstrip("/")
MAX_PER_REQUEST = 500


def call(method, path, body=None, idempotency_key=None):
    headers = {
        "Authorization": f"Bearer {os.environ['TOPSMS_CLIENT_ID']}:{os.environ['TOPSMS_SECRET']}",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                return res.status, json.load(res)
        except urllib.error.HTTPError as e:
            payload = json.loads(e.read() or b"{}")
            # 429 rate limit / 409 same key still running / 502 carrier hand-off: retry with the SAME key
            if e.code in (409, 429, 502) and payload.get("code") != "not_cancellable" and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"TopSMS {e.code} {payload.get('code', '')}: {payload.get('error')}") from None
    raise RuntimeError("unreachable")


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    batch, text, path = sys.argv[1], sys.argv[2], sys.argv[3]
    numbers = [line.strip() for line in open(path, encoding="utf-8") if line.strip()]
    for i in range(0, len(numbers), MAX_PER_REQUEST):
        chunk = numbers[i:i + MAX_PER_REQUEST]
        status, res = call("POST", "/api/sms/send-bulk", {"to": chunk, "text": text},
                           idempotency_key=f"{batch}-{i // MAX_PER_REQUEST}")
        print(f"chunk {i // MAX_PER_REQUEST}: HTTP {status} accepted={res.get('accepted')} "
              f"rejected={res.get('rejected')} price={res.get('price')} {res.get('currency')}")
        for item in res.get("results", []):
            if item.get("status") == "failed":
                print(f"  failed {item.get('to')}: {item.get('error')}")
        if status == 202 and res.get("jobId"):
            job_id = res["jobId"]
            while True:
                _, job = call("GET", f"/api/sms/jobs/{job_id}?results=0")
                print(f"  job {job_id}: {job['status']} sent={job['sent']} failed={job['failed']} queued={job['queued']}")
                if job["status"] in ("done", "failed", "cancelled", "scheduled"):
                    break
                time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
