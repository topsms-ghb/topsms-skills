---
name: topsms-integrations
description: Pick and set up the right TopSMS integration instead of custom code - the remote MCP server (OAuth 2.1, 9 tools) for Claude, ChatGPT, Claude Code and Cursor, the npm package topsms-mcp, the n8n community node n8n-nodes-topsms, the official Make app, WooCommerce, Shopware 6 and JTL-Shop 5 plugins, the PHP library, the HTTP GET API (/api/sms/get, URL authentication opt-in) for routers and monitoring (Zabbix, PRTG, Nagios), e-mail to SMS (number@sms.topsms.eu with a sender allowlist) and SMS appointment reminders from an iCal calendar. Use when someone wants SMS from a shop, workflow tool, AI assistant, device or calendar.
license: MIT
metadata:
  author: TopSMS
  version: "1.0.0"
---

# TopSMS integrations

All integrations use the same account, credit, prices, sender rules, blacklist and test keys as the REST API (`topsms-getting-started`). Overview pages: https://topsms.eu/integrations (EN), https://topsms.eu/de/integrationen (DE), https://www.topsms.cz/api-integrace/pluginy (CZ).

## Which one?

| Situation | Use |
|---|---|
| An AI assistant should send SMS on request | Remote MCP server |
| Workflow automation | n8n node, Make app; Zapier via an HTTP request to the REST API |
| Online shop | WooCommerce, Shopware 6 or JTL-Shop plugin |
| PHP application | `composer require topsms/topsms-php` |
| Router, camera, PLC, PBX, monitoring that can only call a URL | HTTP GET API |
| NAS, UPS, backup software, anything that only sends e-mail alerts | E-mail to SMS |
| Appointment reminders from Google Calendar, Outlook, iCloud | Calendar reminders (dashboard, no code) |
| Your own backend | REST API (`topsms-send-sms`) |

## Remote MCP server (action for agents)

Endpoint: `https://topsms.eu/api/mcp` (also `https://www.topsms.cz/api/mcp`). Transport: Streamable HTTP, stateless JSON-RPC over POST, protocol versions 2025-06-18, 2025-03-26, 2024-11-05. Auth: **OAuth 2.1** sign-in (the client discovers it via `WWW-Authenticate` / protected-resource metadata) **or** the header `Authorization: Bearer <clientId>:<secret>`.

Tools (each calls the same REST handler, so all REST rules apply):

| Tool | Does | REST |
|---|---|---|
| `send_sms` | One SMS, optional `from`, `send_at`, `idempotencyKey` | `POST /api/sms/send` |
| `send_bulk_sms` | Same text to up to 500 numbers (queued above 50) | `POST /api/sms/send-bulk` |
| `get_message_status` | Status and `errorCode` by id or externalId | `GET /api/sms/status/{id}` |
| `get_bulk_job` | Progress of a queued or scheduled send | `GET /api/sms/jobs/{id}` |
| `cancel_scheduled` | Cancel and refund a scheduled or not-started batch | `DELETE /api/sms/jobs/{id}` |
| `verify_send` | Send an OTP (5 per number per hour, 30 s apart) | `POST /api/verify/send` |
| `verify_check` | Check an OTP (5 attempts) | `POST /api/verify/check` |
| `get_credit` | Balance and base price | `GET /api/credit` |
| `get_pricing` | Public price list, no login needed | `/pricing.json` |

Connect:

- **claude.ai / Claude apps**: Settings, Connectors, Add custom connector, URL `https://topsms.eu/api/mcp`, leave OAuth client ID/secret empty, Connect, sign in to TopSMS, Allow. Availability of custom connectors depends on the Claude plan and organisation settings.
- **ChatGPT**: Settings, Apps & Connectors, enable Developer mode (advanced settings; only on some plans), create a connector with the same URL and OAuth, sign in, Allow.
- **Claude Code**: `claude mcp add --transport http topsms https://topsms.eu/api/mcp`, then `/mcp` and sign in in the browser. Or install this repository as a plugin, which registers the same server and these skills in one step (see the README).
- **Cursor and clients without OAuth**: `~/.cursor/mcp.json`

  ```json
  { "mcpServers": { "topsms": { "url": "https://topsms.eu/api/mcp", "headers": { "Authorization": "Bearer CLIENT_ID:SECRET" } } } }
  ```

- **Local stdio** (Claude Desktop and others): `npx -y topsms-mcp` with env `TOPSMS_CLIENT_ID`, `TOPSMS_SECRET` (Node.js 18+). Registry name `io.github.topsms-ghb/topsms-mcp`.

Security: each OAuth connection shows a consent screen and appears in the dashboard as an API key named "OAuth: <app name>"; revoke it there to disconnect. Develop with a test key in the header (sends and charges nothing). Keep tool-call confirmation on in the client: every `send_*` spends real credit. Docs: https://topsms.eu/mcp.

## n8n

Community node **`n8n-nodes-topsms`**: n8n Settings, Community Nodes, Install, `n8n-nodes-topsms`. Credential "TopSMS API": region TopSMS.eu (EUR account) or TopSMS.cz (CZK account), client ID, secret.

Operations: Message (Send, Send Bulk, Get Status), Scheduled Job (Get, Cancel), Verification (Send Code, Check Code), Account (Get Credit). Delivery reports: point the API key's webhook URL at an n8n Webhook node and verify `X-TopSMS-Signature` (`topsms-delivery-reports`). Without the node, an HTTP Request node to `POST https://www.topsms.cz/api/sms/send` works the same.

## Make

Official TopSMS app (invitation link on https://topsms.eu/integrations): modules Send an SMS, Send Bulk SMS, Get a Message Status, Get Credit Balance, and the trigger Watch Delivery Reports.

## Zapier

No dedicated app. Use "Webhooks by Zapier" (paid Zapier plans) with `POST https://www.topsms.cz/api/sms/send`, header `Authorization: Bearer CLIENT_ID:SECRET`, JSON body `{ "to": "...", "text": "..." }`.

## Shop plugins

| Plugin | Requirements | Install |
|---|---|---|
| WooCommerce, "TopSMS - SMS for WooCommerce" 1.0.2 | WordPress 6.5+, WooCommerce 8.0+, PHP 7.4+ | ZIP from https://www.topsms.cz/api-integrace/woocommerce |
| Shopware 6, `TopSmsShopware` 1.0.0 | Shopware 6.6 / 6.7, PHP 8.2+ | ZIP in the Administration (not in the Shopware Store yet) |
| JTL-Shop 5, `topsms_sms` 1.0.0 | JTL-Shop 5.2+, PHP 7.4+ | ZIP in the plugin manager (not in the JTL Extension Store yet); shipping, payment and cancellation SMS during the JTL-Wawi sync |

They send order-status SMS from templates with macros; details and download links on the integrations page. Czech market only: invoice reminders from Fakturoid and iDoklad (dashboard), a Shoptet add-on in preparation.

## HTTP GET API (devices and monitoring)

`GET` or `POST application/x-www-form-urlencoded` to `https://www.topsms.cz/api/sms/get` (also `https://topsms.eu/api/sms/get`), scope `send`. Same rules as `POST /api/sms/send`.

| Parameter | |
|---|---|
| `to`, `text` | required; URL-encode (`%2B49...`, UTF-8) |
| `from`, `send_at` | optional, as in the REST API |
| `ref` | your reference; the same `ref` within 24 h does not send again (it becomes the Idempotency-Key) |
| `format=json` | JSON response instead of text (also with `Accept: application/json`) |
| `client_id` + `secret`, or `key=clientId:secret` | only when the device cannot send a header |

Authentication, best first: `Authorization: Bearer clientId:secret` header; `client_id`/`secret` in the POST form body; key in the **query string only if "Allow URL authentication" is enabled for that key** (off by default, otherwise `403 url_auth_disabled`). URLs end up in device, proxy and server logs: use a dedicated key with scope `send` only and an IP whitelist.

Response: one line of text, `OK <messageId>` or `ERROR <code> <message>`, with the REST status codes. Link-preview bots (Slack, Teams, WhatsApp...) get `403 link_preview` and send nothing; `HEAD` returns 405.

```bash
curl -H "Authorization: Bearer $TOPSMS_CLIENT_ID:$TOPSMS_SECRET" \
  "https://www.topsms.cz/api/sms/get?to=%2B4915112345678&text=UPS%20on%20battery&ref=ups-42"
# OK cmh3x9k2a0001qz8l5v7w2abc
```

Zabbix, PRTG and Nagios recipes: https://topsms.eu/docs#http-get-api.

## E-mail to SMS

Send an e-mail to `<number>@sms.topsms.eu` (or `@sms.topsms.cz`); the body becomes the SMS.

- Enable per API key (dashboard, API, "GET & e-mail"): turn on E-mail to SMS and list allowed senders, exact addresses (`alerts@company.com`) or your own domain (`@company.com`). Whole public mail domains (gmail.com, gmx.de, seznam.cz...) cannot be allowed.
- Address: `+4915112345678@...`, `4915112345678@...`, `004915112345678@...` or the national format of the account's country (`015112345678@...`). Up to 10 numbers in To and Cc.
- Accepted only if the From address (and envelope sender or its domain) is allowed **and** DMARC, aligned DKIM or aligned SPF passes, or the address carries the key token: `4915112345678.tok_xxxxxxxxxxxxxxxx@sms.topsms.eu` (token shown at the key; use it for devices whose mail server has no SPF/DKIM).
- Text: plain-text part (HTML converted), quoted replies and signature after `-- ` removed, whitespace collapsed, max 1,600 characters; empty body uses the subject.
- 60 e-mails per hour per key and per sender address. Unauthorized mail is rejected during SMTP delivery with no reply. Failed sends (credit, number) bounce with the reason. The same Message-ID within 24 h is not sent twice. A test key processes but sends nothing. Sender name = the account's default sender.

## SMS appointment reminders from a calendar

No code: paste the private iCal (ICS) link of Google Calendar, Outlook/Microsoft 365 or iCloud in the dashboard (Calendar reminders). TopSMS reads the next 7 days every 15 minutes, finds a mobile number in the title, description or location, and sends one reminder per appointment 1-72 h before (default 24). No SMS between 21:00 and 08:00 (moved to 08:00, or 18:00 the evening before), none less than 30 minutes before; cancelled appointments are skipped, moved ones rescheduled, opted-out numbers skipped. Pages: https://topsms.eu/calendar-sms-reminders, https://www.topsms.cz/pripominky-z-kalendare.

## PHP library

```bash
composer require topsms/topsms-php
```

Sending, status and webhook verification; source https://github.com/topsms-ghb/topsms-php.
