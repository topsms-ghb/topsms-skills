---
name: topsms-getting-started
description: Set up the TopSMS SMS API (topsms.eu for Germany, Austria and the EU in EUR; topsms.cz for Czechia and Slovakia in CZK) - accounts, API keys (Bearer clientId:secret), scopes, test keys, base URL, the first SMS in curl, PHP, Python or Node.js, and the error format. Use when a user wants to send SMS from code with TopSMS, asks how to authenticate, gets 401/402/403/429 errors, or is starting a TopSMS integration.
license: MIT
metadata:
  author: TopSMS
  version: "1.0.0"
---

# TopSMS: getting started

TopSMS is a prepaid SMS gateway. One REST API serves both brands:

| | topsms.eu | topsms.cz |
|---|---|---|
| Market | Germany, Austria, rest of EU (EN/DE site) | Czechia, Slovakia (CZ site) |
| Account currency | EUR | CZK |
| Amounts in API responses | EUR, prices to 4 decimals | CZK |
| Docs | https://topsms.eu/docs, https://topsms.eu/de/docs | https://www.topsms.cz/api-integrace/rest-api |

The account currency is fixed by where the account was created. Every JSON response made with an API key carries `"currency": "EUR"` or `"currency": "CZK"`; never assume one. A new account must confirm its mobile number before it can send.

## Base URL

```
https://www.topsms.cz
```

This is the documented REST base for **all** accounts, including topsms.eu accounts (it is the `servers` entry of the OpenAPI spec at https://topsms.eu/openapi.yaml). The remote MCP server and the HTTP GET API are also documented on `https://topsms.eu` (`/api/mcp`, `/api/sms/get`).

## Authentication

Create a key in the dashboard: https://www.topsms.cz/dashboard/api (section API keys). You get a **client ID** and a **secret**; the secret is shown once, only its bcrypt hash is stored.

```
Authorization: Bearer <clientId>:<secret>
```

- Scopes per key: `send` (send SMS, Verify API, cancel jobs) and `read` (status, jobs, credit). Missing scope = `403 Missing scope: send`.
- Optional per key: IP whitelist (other IPs get 403), webhook URL (see the `topsms-delivery-reports` skill), rate limit (default 60 requests/min, configurable up to 1000; a bulk request counts once).
- Up to 10 active keys per account; each message is attributed to the key that sent it. Revoke a key in the dashboard at any time.
- More than 20 wrong secrets per minute for one client ID returns 429 before the secret is even checked.
- Never put keys in source code, prompts, logs or front-end JavaScript. Read them from environment variables (`TOPSMS_CLIENT_ID`, `TOPSMS_SECRET`) or a secret store.

## Test keys (use them first)

Tick "test key" when creating a key. A test key:

- sends nothing and charges nothing, but runs the same validation (number, sender, scheduling) and returns the same response shape plus `"test": true`;
- produces a simulated delivery report after 2-4 s, also as a webhook with `"test": true`;
- number ending `0000` simulates `failed`, ending `0001` simulates `expired`, anything else `delivered`;
- on the Verify API returns `testCode` so you can complete the flow without a phone.

Agents and CI should always develop against a test key.

## First SMS

`POST /api/sms/send`, JSON body `{ "to": "+4915112345678", "text": "..." }`. Phone numbers in E.164 (`+` country code number). Details: `topsms-send-sms` skill.

```bash
curl -sS https://www.topsms.cz/api/sms/send \
  -H "Authorization: Bearer $TOPSMS_CLIENT_ID:$TOPSMS_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"to":"+4915112345678","text":"Your order 1024 has shipped."}'
```

Ready-to-run versions: [scripts/send_sms.py](scripts/send_sms.py), [scripts/send_sms.mjs](scripts/send_sms.mjs), [scripts/send_sms.php](scripts/send_sms.php). Each reads the key from the environment and the number and text from arguments.

Success (`200`):

```json
{
  "ok": true,
  "id": "cmh3x9k2a0001qz8l5v7w2abc",
  "externalId": "8d1f...",
  "to": "+4915112345678",
  "from": "TopSMS",
  "smsCount": 1,
  "price": 0.084,
  "status": "sent",
  "currency": "EUR"
}
```

- `id` is the TopSMS message ID; use it for `GET /api/sms/status/{id}`. `status: "sent"` means accepted by the network, not delivered yet.
- `smsCount` = billed segments, `price` = total for this message in the account currency.
- Test key: additionally `"test": true`, `externalId` starts with `test-`.
- `senderFallback: true` + `requestedFrom` appear when the requested sender name could not be used yet and the SMS went out as `TopSMS`.

Check the balance with `GET /api/credit` (scope `read`):

```json
{ "ok": true, "credit": 12.4, "currency": "EUR", "smsPrice": 0.0403 }
```

`smsPrice` is the account's base price per segment (for EUR accounts this is the converted CZ/SK base tier; the EU destination price is listed at https://topsms.eu/pricing.json). Public prices: https://topsms.eu/pricing (EU) and https://www.topsms.cz/cenik (CZ).

## Errors

Errors are JSON `{ "error": "<human readable>", "code": "<machine code, when available>" }` (plus `currency` for API-key calls). Branch on the HTTP status and `code`, never on the English text.

| Status | Meaning | Typical `code` | Retry? |
|---|---|---|---|
| 400 | Missing `to`/`text`, invalid number, blacklisted number, bad `send_at` or Idempotency-Key | `invalid_send_at`, `invalid_idempotency_key` | No, fix the request |
| 401 | Missing/malformed header, unknown or revoked key, wrong secret | (none) | No |
| 402 | Not enough prepaid credit | `insufficient_credit` | After top-up |
| 403 | Missing scope, IP not whitelisted, account inactive, sender name not allowed, links before first paid top-up | `sender_not_allowed`, `sender_protected`, `sender_needs_topup`, `urls_need_topup` | No |
| 404 | Message, job or verification not found (or not yours) | | No |
| 409 | Same Idempotency-Key still running; job can no longer be cancelled | `idempotency_in_progress`, `not_cancellable`, `campaign_job` | 409 in-progress: yes, after a few seconds |
| 422 | Idempotency-Key reused with a different body | `idempotency_mismatch` | No |
| 429 | Rate limit of the key, Verify limits, too many wrong secrets | `rate_limited`, `cooldown` (Verify) | Yes, with backoff |
| 500 `record_failed` | SMS was sent but not recorded; credit refunded | `record_failed` | **No, do not resend** |
| 502 | Carrier hand-off failed, credit refunded | | Yes, with the same Idempotency-Key |

Always send an `Idempotency-Key` header on sending requests so retries can never double-send (see `topsms-send-sms`).

## Where to go next

- Sending, bulk, scheduling, sender names, phone formats: `topsms-send-sms`
- Delivery status and signed webhooks: `topsms-delivery-reports`
- One-time codes: `topsms-otp-verify`
- Segment counting and cost: `topsms-sms-length`
- No-code, plugins, HTTP GET, e-mail to SMS, MCP: `topsms-integrations`
- Consent, opt-out, GDPR: `topsms-compliance`
- Machine-readable: OpenAPI https://topsms.eu/openapi.yaml, https://topsms.eu/llms.txt, https://topsms.eu/llms-full.txt
- PHP library: `composer require topsms/topsms-php` (https://github.com/topsms-ghb/topsms-php)
