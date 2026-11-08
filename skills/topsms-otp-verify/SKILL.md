---
name: topsms-otp-verify
description: Implement SMS one-time passcodes (OTP, 2FA, phone number verification, double opt-in) with the TopSMS Verify API - POST /api/verify/send and POST /api/verify/check, parameters (length, ttl, locale cs/en/de, brand), limits (5 codes per number per hour, 30 s cooldown, 5 attempts), test keys with testCode, and security practice (TopSMS stores only a hash; never log or return codes). Use when adding SMS verification or login codes with TopSMS.
license: MIT
metadata:
  author: TopSMS
  version: "1.0.0"
---

# OTP with the TopSMS Verify API

TopSMS generates the code, sends it, stores only an HMAC of it, and checks the user's answer. Your backend never needs to see or store the code. Both endpoints need scope `send`. Base URL `https://www.topsms.cz`.

## Flow

1. Backend calls `POST /api/verify/send` with the user's number, keeps the returned `id` in the user's session (server side).
2. User types the code from the SMS.
3. Backend calls `POST /api/verify/check` with `id` and `code`, and continues only if `valid` is `true`.

Never call these endpoints from the browser or a mobile app directly: that would expose your API key.

## Send a code

```http
POST /api/verify/send
Authorization: Bearer <clientId>:<secret>
Content-Type: application/json
Idempotency-Key: signup-8f3a-otp-1

{ "to": "+4915112345678", "brand": "MyShop", "locale": "de", "length": 6, "ttl": 300 }
```

| Field | Default | Rules |
|---|---|---|
| `to` | required | Phone number, E.164 (same normalisation as sending, see `topsms-send-sms`) |
| `brand` | none | Up to 20 characters (letters incl. accents, digits, space, `.`, `_`, `-`; other characters are removed); shown as `MyShop: ...` |
| `length` | 6 | 4-8 digits |
| `ttl` | 300 | Validity in seconds, 60-1800 |
| `locale` | `cs` | `en`, `de` or `cs`. **Set it**: the default is Czech |
| `from` | `TopSMS` | Sender name (same rules as sending). Not the account default sender |

The SMS text is fixed per locale and stays in one GSM-7 segment:

- `en`: `MyShop: your verification code is 482913. Valid for 5 min. Do not share it.`
- `de`: `MyShop: Ihr Bestätigungscode lautet 482913. Gültig 5 Min. Geben Sie ihn nicht weiter.`
- `cs`: `MyShop: vas overovaci kod je 482913. Plati 5 min. Nikomu ho nesdelujte.`

Response `200`:

```json
{ "ok": true, "id": "cmhv0x...", "to": "+4915112345678", "status": "pending",
  "expiresAt": "2026-11-08T09:05:00.000Z", "messageId": "cmhv0y...", "price": 0.084, "currency": "EUR" }
```

With a **test key** nothing is sent or charged, `messageId` is `null`, and the response adds `"test": true, "testCode": "123456"` (the first `length` digits of `12345678`). Use this in automated tests; never enable test keys in production.

Errors: `400 invalid_number`, `401 unauthorized`, `402 insufficient_credit`, `429 rate_limited` (5 codes per number per hour reached), `429 cooldown` with `retryAfter` seconds (less than 30 s since the previous code to that number), `502 send_failed`.

Sending a new code to the same number cancels the previous pending code (its status becomes `canceled`).

## Check a code

```http
POST /api/verify/check
{ "id": "cmhv0x...", "code": "482913" }
```

Instead of `id` you may send `to`; the latest verification for that number is checked. Prefer `id`, it cannot be confused with a code sent from another flow.

Response is always `200` when the verification exists:

```json
{ "valid": true,  "status": "approved", "id": "cmhv0x..." }
{ "valid": false, "status": "pending",  "attemptsLeft": 3, "id": "cmhv0x..." }
{ "valid": false, "status": "expired",  "id": "cmhv0x..." }
```

| `status` | Meaning |
|---|---|
| `approved` | Correct code. A second check of the same verification returns `valid: false, status: "approved"`, so a code works only once |
| `pending` | Wrong code, `attemptsLeft` more tries |
| `failed` | 5 wrong attempts, the code is dead; send a new one |
| `expired` | TTL passed |
| `canceled` | A newer code was sent to the number |

Errors: `400 invalid_code_format` (code must be 4-8 digits; spaces are stripped), `400 missing_id`, `404 not_found`.

## Limits (enforced by TopSMS)

- 5 codes per number per hour (per account), at least 30 s between two codes to the same number
- 5 check attempts per code
- 60-1800 s validity

Add your own limits on top: per IP, per account and per session, and a CAPTCHA before `send` on public sign-up forms, to stop SMS pumping (attackers triggering codes to premium or foreign numbers you pay for). Restrict the countries you accept to the ones you serve.

## Security rules

- Do not log codes, do not return them to the client, do not put them in analytics or error trackers. With the Verify API you never receive the live code at all; keep it that way.
- Keep `id` server-side (session), not in a URL.
- Compare nothing yourself: rely on `valid` from `/api/verify/check`.
- Show a neutral message for wrong codes and do not reveal whether a number exists in your system.
- After `approved`, mark the number as verified in your own database; do not re-check.
- An OTP SMS is transactional. Do not add marketing text to it (`topsms-compliance`).

## Runnable example

[scripts/otp_demo.py](scripts/otp_demo.py) runs send + check interactively. With a test key it prints the `testCode` so you can complete the flow without a phone.

## MCP equivalent

The TopSMS MCP server exposes the same calls as the tools `verify_send` and `verify_check` (see `topsms-integrations`).
