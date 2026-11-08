---
name: topsms-send-sms
description: Send SMS through the TopSMS REST API correctly - single SMS (POST /api/sms/send), bulk up to 500 recipients (POST /api/sms/send-bulk, queue and jobId above 50), scheduled sending with send_at and cancellation, Idempotency-Key for safe retries, sender name (Sender ID) rules for Czechia/Slovakia vs the rest of the EU, protected brand names, the links-after-first-top-up rule, and E.164 phone number formats. Use when writing or reviewing code that sends SMS via TopSMS, or when a send returns 400/403/409/422.
license: MIT
metadata:
  author: TopSMS
  version: "1.0.0"
---

# Sending SMS with TopSMS

Base URL `https://www.topsms.cz`, header `Authorization: Bearer <clientId>:<secret>`, scope `send`. Setup and error table: `topsms-getting-started`.

## Decision guide

| Need | Endpoint |
|---|---|
| One recipient, now or later | `POST /api/sms/send` |
| Same text to many, or a personalised text per recipient (max 500 per request) | `POST /api/sms/send-bulk` |
| Progress of a queued/scheduled batch | `GET /api/sms/jobs/{jobId}` (scope `read`) |
| Cancel a scheduled or not-yet-started batch | `DELETE /api/sms/jobs/{jobId}` |
| Device that can only call a URL | `GET /api/sms/get` (see `topsms-integrations`) |

## Single SMS

```http
POST /api/sms/send
Content-Type: application/json
Idempotency-Key: 7b0e2c1e-5c1a-4b7e-9d51-0f6a9c1d2e33

{ "to": "+4915112345678", "text": "Your order 1024 has shipped.", "from": "MyShop" }
```

| Field | Required | Notes |
|---|---|---|
| `to` | yes | Phone number, E.164 recommended (see Phone numbers) |
| `text` | yes | Sent verbatim. The API does **not** replace placeholders such as `{name}`; build the final text yourself. Keep it short: segment rules in `topsms-sms-length`. |
| `from` | no | Sender name, max 11 characters. Omit to use the account's default sender (see Sender names) |
| `send_at` | no | Schedule (see Scheduling). `sendAt` is accepted as an alias |

Response `200`: `{ ok, id, externalId, to, from, smsCount, price, status: "sent", currency }`, optionally `senderFallback: true` and `requestedFrom`, and `test: true` for test keys. `to` is the normalised number.

## Bulk

```http
POST /api/sms/send-bulk
{ "to": ["+4915112345678", "+436641234567"], "text": "Shop closed on Monday.", "from": "MyShop" }
```

or one text per recipient:

```json
{ "messages": [ { "to": "+4915112345678", "text": "Hi Anna, your table is ready." },
                { "to": "+436641234567",  "text": "Hi Jonas, your table is ready." } ] }
```

Rules (from the server code):

- At most **500** recipients per request, otherwise `400`. Split larger lists and give each chunk its own Idempotency-Key.
- One `from` for the whole request; the sender rules below are evaluated for all recipients together.
- Credit is checked for the whole batch before anything is sent (`402` if short).
- Invalid numbers, empty texts and blacklisted numbers are reported per item and are not charged; if no item is sendable the response is `400` with the per-item `results`.
- **Up to 50 sendable recipients**: processed synchronously, `200` with `{ ok, total, accepted, rejected, price, results: [{ to, status: "sent"|"failed", id, externalId, price, error }] }`.
- **More than 50**, or `"async": true`, or `send_at`: `202` with `{ ok, queued: true, jobId, statusUrl, total, accepted, rejected, price, results }`; credit is deducted immediately and a worker sends. Poll `GET /api/sms/jobs/{jobId}` or wait for webhooks.
- A bulk request counts as one request against the key's rate limit.

Job status (`GET /api/sms/jobs/{jobId}`, add `?results=0` for counters only):

```json
{ "id": "cmg...", "status": "running", "sendAt": null, "total": 120, "sent": 80, "failed": 1, "queued": 39,
  "price": 10.08, "createdAt": "...", "startedAt": "...", "finishedAt": null, "error": null,
  "results": [ { "id": "...", "to": "+49...", "status": "delivered", "externalId": "...", "price": 0.084, "error": null, "errorCode": null } ] }
```

Job `status`: `scheduled`, `queued`, `running`, `done`, `failed`, `cancelled`. `results` lists at most 500 messages.

## Scheduling (`send_at`)

- ISO 8601 **with a time zone** (`2026-12-01T09:00:00+01:00` or `...Z`), or a Unix timestamp (seconds or milliseconds). A string without a zone is rejected: `400 invalid_send_at`.
- At most **30 days** ahead. More than 5 minutes in the past is rejected. A time within the next 60 seconds is treated as "send now".
- Response `202`: `{ ok, scheduled: true, id, jobId, statusUrl, status: "scheduled", sendAt, smsCount, price, ... }`. Credit is deducted at scheduling time.
- Cancel with `DELETE /api/sms/jobs/{jobId}` (scope `send`): `200 { ok, id, status: "cancelled", cancelled, refunded }`; `409 not_cancellable` once sending has started; `409 campaign_job` for dashboard campaigns.
- Pick the local time zone of the **recipient** (Europe/Berlin, Europe/Vienna, Europe/Prague) and avoid night hours (see `topsms-compliance`).

## Idempotency (always use it)

Send `Idempotency-Key: <1-255 printable ASCII chars, e.g. a UUID>` on `/api/sms/send`, `/api/sms/send-bulk` and `/api/verify/send`.

- Same key + same endpoint + same body within 24 h: the original response is returned with header `Idempotent-Replayed: true`; nothing is sent again.
- Same key, different body or endpoint: `422 idempotency_mismatch`. First request still running: `409 idempotency_in_progress` (retry in a few seconds).
- Responses 401, 402, 403, 408, 409, 429 and 5xx are not stored, so the same key can be retried after fixing the cause. Exception: `500 record_failed` is stored, because that SMS was already sent.
- Derive the key from your own business event (`order-1024-shipped`) rather than a random value per attempt, so a crashed worker that restarts cannot double-send.
- Keys are scoped to the API key that sent them.

## Sender names (`from`)

What actually appears as the sender depends on the destination:

1. **Omitted**: the account's default sender (Dashboard, Sender ID, "Set as default") if it is active, otherwise `TopSMS`.
2. **`"TopSMS"`**: always allowed.
3. **A name approved on the account**: used as is when it is active with the Czech/Slovak operators, or when **all** recipients are outside Czechia and Slovakia. Otherwise the SMS goes out as `TopSMS` and the response contains `senderFallback: true, requestedFrom: "<name>"`.
4. **A new name** (not yet on the account): accepted automatically only when the account is approved, has made at least one **paid top-up** (the free starting credit does not count), and the name is valid and not a protected brand. It is then created as approved; outside CZ/SK it is used immediately, to CZ/SK numbers it falls back to `TopSMS` until registered with the operators.

Errors (`403`): `sender_needs_topup` (no paid top-up yet), `sender_protected` (resembles a brand or institution, needs a manual request in the dashboard), `sender_not_allowed` (invalid name or account not approved). In all three cases you can retry without `from`.

Valid name: 3-11 characters, starts with a letter or digit, then letters, digits, space, `.`, `_`, `&`, `-`, no double spaces, at least one letter (a pure number would impersonate a phone number). Protected names include banks, payment services, carriers, parcel services, authorities and big tech brands, also with look-alike spellings (`PayPaI`, `Amaz0n`, `DHL-Info`). Czech and Slovak operators register sender names in batches; on topsms.cz this is a one-time fee per name (see https://www.topsms.cz/produkty/sender-id).

Recipients cannot reply to an alphanumeric sender name. Put a reply channel (link, e-mail, phone) in the text when you expect answers.

## Links in the text

Messages containing a link (`http(s)://...`, `www....`, or a bare domain such as `example.com/x` or `bit.ly/...`) are rejected with `403 urls_need_topup` until the account has made its first paid top-up (anti-phishing protection for free trial credit). Test keys are not affected. Prefer your own domain over public URL shorteners.

## Phone numbers

Send **E.164**: `+` then country code then number, no spaces needed (`+4915112345678`, `+436641234567`, `+420601234567`, `+421901234567`). The server normalises:

- removes spaces and any characters other than digits and `+`; `00` prefix becomes `+`;
- a bare 9-digit number starting with 6 or 7 is treated as Czech (`601234567` becomes `+420601234567`);
- any other number without `+` is read as international: `4915112345678` works, but a German national number like `015112345678` becomes `+015...` and is rejected. Convert national numbers yourself (for example with libphonenumber) before calling the API;
- Czech numbers: only mobile ranges are accepted (601-608, 702-705, 720-739, 770-779, 790-799); Slovak: only `+4219xxxxxxxx`; Czech premium-rate `+42090...` is rejected;
- invalid numbers return `400 Invalid phone number. Use international format (+420…, +421…, +43…).`

Numbers on the TopSMS blacklist are rejected with `400` (single) or a failed item (bulk). This blacklist is kept by TopSMS; the opt-out flag on your dashboard contacts is applied by dashboard campaigns and calendar reminders, **not** by REST API calls, so filter opted-out numbers in your own code before sending. See `topsms-compliance`.

## Runnable example

[scripts/send_bulk.py](scripts/send_bulk.py): bulk send in chunks of 500 with deterministic idempotency keys, then polls the job. Run it with a test key first.

## Checklist for generated code

- [ ] Key from environment or secret store, never hard-coded
- [ ] Numbers normalised to E.164 before the call
- [ ] Final text built locally (no `{placeholders}`), length checked (`topsms-sms-length`)
- [ ] `Idempotency-Key` derived from the business event
- [ ] Handles `senderFallback`, `402`, `403 sender_*`, `403 urls_need_topup`, `429` with backoff
- [ ] Never retries `500 record_failed`
- [ ] Stores the returned `id` to match delivery webhooks
