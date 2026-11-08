---
name: topsms-delivery-reports
description: Track whether TopSMS messages were delivered - the status endpoint GET /api/sms/status/{id}, message statuses and errorCode values, push delivery reports by webhook (payload, X-TopSMS-Signature HMAC-SHA256 verification over the raw body, 3 attempts at 0 s / +30 s / +2 min, 5 s timeout) and test webhooks. Use when implementing a TopSMS webhook receiver, verifying webhook signatures, polling delivery status, or debugging why a message was not delivered.
license: MIT
metadata:
  author: TopSMS
  version: "1.0.0"
---

# Delivery reports

A successful send (`status: "sent"`) only means the network accepted the SMS. The final result arrives later as a delivery report from the carrier. You can **poll** it or receive it **by webhook**. Prefer webhooks; poll as a fallback.

## Statuses

| Message `status` | Meaning | Final? |
|---|---|---|
| `queued` | In a TopSMS queue (bulk job or scheduled send) | no |
| `pending` | Being handed to the carrier | no |
| `sent` | Accepted by the carrier, waiting for the delivery report | no |
| `delivered` | Delivered to the handset | yes |
| `failed` | Not delivered, see `errorCode` | yes |
| `expired` | Validity ran out (phone off or out of coverage the whole time) | yes |

`errorCode` (only on `failed`/`expired`):

| `errorCode` | Meaning |
|---|---|
| `expired` | Phone was off or unreachable for the whole validity period |
| `undelivered` | Carrier returned it as undeliverable (number not existing or inactive; some foreign networks also report a temporarily unreachable phone this way) |
| `rejected` | Carrier refused it (recipient blocks business SMS, or sender/content not accepted) |
| `deleted` | Carrier cancelled it before delivery |
| `unknown` | Carrier returned no result |
| `repeated_failure` | Delivery to this number has failed at least three times within 90 days; stop sending to it |
| `not_sent` | Never left TopSMS; the price was refunded |

Billing: an SMS that was handed to the carrier is billed even if it is later reported `failed` or `expired`. Only `not_sent` and hand-off errors (HTTP 502 on send) are refunded.

## Polling: `GET /api/sms/status/{id}`

Scope `read`. `{id}` is the TopSMS `id` from the send response or the carrier `externalId`.

```bash
curl -sS -H "Authorization: Bearer $TOPSMS_CLIENT_ID:$TOPSMS_SECRET" \
  https://www.topsms.cz/api/sms/status/cmh3x9k2a0001qz8l5v7w2abc
```

```json
{
  "id": "cmh3x9k2a0001qz8l5v7w2abc",
  "externalId": "8d1f...",
  "to": "+4915112345678",
  "from": "MyShop",
  "text": "Your order 1024 has shipped.",
  "status": "delivered",
  "price": 0.084,
  "carrier": "262.1",
  "createdAt": "2026-11-08T09:00:00.000Z",
  "deliveredAt": "2026-11-08T09:00:04.000Z",
  "failedAt": null,
  "errorMessage": null,
  "errorCode": null,
  "currency": "EUR"
}
```

`carrier` is the network as MCC.MNC (e.g. `230.1`) when known. `404` = not found or not yours. Test-key messages answer with `"test": true`. Poll with backoff (for example after 5 s, 30 s, 2 min, 10 min) and stop at a final status; for batches use `GET /api/sms/jobs/{jobId}` instead of one call per message.

## Webhooks

Set a **webhook URL on the API key** (dashboard, API keys). When the key is created or edited with a webhook URL, TopSMS generates a **webhook secret** (48 hex characters) and shows it once. Store it like a password.

Only messages sent **with that API key** produce webhooks (not dashboard sends or campaigns). TopSMS sends one event per final status change (`delivered`, `failed`, `expired`).

Request:

```http
POST <your webhook URL>
Content-Type: application/json
User-Agent: TopSMS-Webhook/1.1
X-TopSMS-Signature: sha256=5f0c...e91a

{"event":"sms.status","id":"cmh3x9k2a0001qz8l5v7w2abc","externalId":"8d1f...","to":"+4915112345678","from":"MyShop","status":"delivered","price":0.084,"currency":"EUR","deliveredAt":"2026-11-08T09:00:04.000Z","failedAt":null,"errorMessage":null,"errorCode":null,"sentAt":"2026-11-08T09:00:05.120Z"}
```

| Field | Notes |
|---|---|
| `event` | Always `sms.status` |
| `id` / `externalId` | Same IDs as the send response; match on `id` |
| `status` | `delivered`, `failed` or `expired` |
| `price`, `currency` | Price of the message in the account currency (EUR to 4 decimals) |
| `errorCode`, `errorMessage` | As in the table above; `errorMessage` is human-readable and may be Czech, do not parse it |
| `sentAt` | When this webhook was sent (not when the SMS was sent) |
| `test` | `true` for test-key messages and for the dashboard "send test webhook" button (that test event has `id: "test_webhook"` and no `currency`) |

### Signature

```
X-TopSMS-Signature: sha256=<hex( HMAC-SHA256( key = webhook secret as UTF-8 text, message = raw request body ) )>
```

- Compute the HMAC over the **raw body bytes exactly as received**. Parsing and re-serialising the JSON changes the bytes and breaks the check.
- The key is the secret string itself (its UTF-8 bytes), not hex-decoded.
- Compare in constant time (`hmac.compare_digest`, `crypto.timingSafeEqual`).
- The header is only sent when the key has a webhook secret. If it is missing, treat the request as unauthenticated.
- There is no timestamp in the signature: protect against replays by de-duplicating on `id` + `status` and ignoring events older than what you already stored.

Ready-made receivers: [scripts/webhook_receiver.py](scripts/webhook_receiver.py) (standard library) and [scripts/webhook_receiver.mjs](scripts/webhook_receiver.mjs) (Node.js, no dependencies). Both verify the signature and print the event. Run [scripts/sign_test.py](scripts/sign_test.py) to send yourself a correctly signed sample.

### Delivery rules (retry schedule)

- Up to **3 attempts**: immediately, then 30 s later, then 2 minutes after that.
- Each attempt times out after **5 s**. Answer quickly with any `2xx` and do the work asynchronously.
- Anything else counts as failure, **including 3xx**: redirects are not followed, so register the final HTTPS URL.
- The URL must resolve to a public address (private, loopback and link-local targets are blocked).
- After the third failure the event is not sent again. Reconcile with `GET /api/sms/status/{id}` for messages still at `sent` after some minutes.
- Every attempt (status, duration, error, payload) is logged in the dashboard under the API key (Log, Webhooks), and the dashboard has a "send test webhook" button.

### Receiver checklist

- [ ] Read the raw body before any JSON middleware (Express: `express.raw({ type: 'application/json' })`; Flask: `request.get_data()`; PHP: `file_get_contents('php://input')`)
- [ ] Verify `X-TopSMS-Signature` in constant time, reject with 401 otherwise
- [ ] Respond `2xx` within 5 s
- [ ] Idempotent processing keyed by `id` + `status`
- [ ] Handle `test: true` events without side effects in production data
- [ ] Never log the webhook secret

## Germany note

Some German networks report "undelivered" immediately when the phone is switched off. The account setting "automatic retry" (dashboard, account settings) re-sends up to 6 times within 8 hours; each attempt is billed as a new SMS and `externalId` then belongs to the last attempt.
