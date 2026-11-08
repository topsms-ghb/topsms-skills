#!/usr/bin/env python3
"""SMS segment counter with the same rules and character tables TopSMS uses for billing.

  python3 sms_length.py "Your text"
  echo "Your text" | python3 sms_length.py -

Prints encoding, length, segments and the characters that force UCS-2, plus a GSM-7-safe
suggestion (German umlauts kept, typography replaced, other diacritics removed).
Standard library only, Python 3.8+.
"""
import json
import math
import sys
import unicodedata

GSM7_BASE = ("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡"
             "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
GSM7_EXT = "^{}\\[~]|€"
TYPO = {"–": "-", "—": "-", "−": "-", "„": '"', "“": '"', "”": '"', "»": '"', "«": '"',
        "‚": "'", "‘": "'", "’": "'", "…": "...", " ": " ", " ": " ", " ": " "}


def utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def analyze(text: str) -> dict:
    extras, problems, gsm = 0, [], True
    for ch in text:
        if ch in GSM7_EXT:
            extras += 1
        elif ch not in GSM7_BASE:
            gsm = False
            if ch not in problems and len(problems) < 12:
                problems.append(ch)
    if gsm:
        n = len(text) + extras
        parts = 0 if n == 0 else 1 if n <= 160 else math.ceil(n / 153)
        return {"encoding": "GSM-7", "length": n, "segments": parts, "limit": "160/153", "problem_chars": []}
    n = utf16_len(text)
    parts = 0 if n == 0 else 1 if n <= 70 else math.ceil(n / 67)
    return {"encoding": "UCS-2", "length": n, "segments": parts, "limit": "70/67", "problem_chars": problems}


def to_gsm7_keep_umlauts(text: str) -> str:
    out = []
    for ch in text:
        if ch in GSM7_BASE or ch in GSM7_EXT:
            out.append(ch)
        elif ch in TYPO:
            out.append(TYPO[ch])
        else:
            base = "".join(c for c in unicodedata.normalize("NFD", ch) if not unicodedata.combining(c))
            out.append(base if base and all(c in GSM7_BASE or c in GSM7_EXT for c in base) else ch)
    return "".join(out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    text = sys.stdin.read().rstrip("\n") if sys.argv[1] == "-" else sys.argv[1]
    r = analyze(text)
    print(f"encoding={r['encoding']} length={r['length']} segments={r['segments']} "
          f"limit={r['limit']} problem_chars={json.dumps(r['problem_chars'], ensure_ascii=False)}")
    if r["encoding"] == "UCS-2":
        g = to_gsm7_keep_umlauts(text)
        rg = analyze(g)
        print(f"gsm7_version: {g}  ({rg['encoding']}, {rg['length']}, {rg['segments']} segment"
              f"{'' if rg['segments'] == 1 else 's'})")
