---
name: topsms-compliance
description: Build compliant business SMS with TopSMS - transactional vs marketing messages, consent (§ 7 UWG in Germany, § 174 TKG 2021 in Austria, Act 480/2004 Coll. in Czechia), double opt-in with the Verify API, opt-out handling (why "reply STOP" does not work with a sender name, where TopSMS enforces opt-outs and where your code must), sending hours, sender identification, GDPR basics and the data processing agreement. General information, not legal advice. Use when designing SMS campaigns, notification templates, consent flows or unsubscribe handling with TopSMS.
license: MIT
metadata:
  author: TopSMS
  version: "1.0.0"
---

# SMS compliance with TopSMS

This is general information for developers, compiled from TopSMS documentation and the cited laws. It is **not legal advice**. Laws change and details matter; for a binding assessment ask a lawyer or your data protection officer. Do not present anything here to users as legal advice, and do not invent legal requirements that are not listed.

## 1. Classify every message

| Transactional (service) | Marketing (advertising) |
|---|---|
| Order and shipping updates, appointment reminders the customer booked, OTP and login codes, invoice due notices, "your repair is ready" | Discounts, new products, newsletters, review requests, "we miss you", birthday vouchers, satisfaction surveys used to promote sales |
| Needs a GDPR legal basis (usually the contract), no advertising consent | Needs prior consent (exceptions below) and an opt-out in every message |

A transactional SMS with one promotional sentence added ("...shipped. 10 % off your next order with code X") counts as advertising as a whole. Keep the two kinds in separate templates and, ideally, separate sending code paths.

## 2. Consent for marketing

- **Germany**: § 7 para. 2 no. 2 UWG requires the recipient's **prior express consent** for advertising by electronic mail, which includes SMS; it applies to consumers and businesses. The narrow existing-customer exception in § 7 para. 3 UWG needs all four conditions: number obtained in connection with a sale, advertising for your own similar goods or services, no objection, and a clear notice at collection and in every message that the customer can object at any time at no extra cost.
- **Austria**: § 174 TKG 2021 requires prior consent for SMS advertising.
- **Czechia**: Act No. 480/2004 Coll. requires consent, or an existing customer relationship for similar products with an easy way to opt out.
- Consent must exist **before** the first marketing SMS; an SMS asking for consent is itself advertising.
- Pre-ticked boxes or consent buried in terms are not enough. Keep proof.

**Double opt-in** is the usual proof: the person enters the number and ticks a consent box, then confirms with a code sent by SMS. Implement the confirmation with the Verify API (`topsms-otp-verify`); the code SMS is transactional. Store per number: consent text and version, timestamps of request and confirmation, IP or session, purpose, and the date and way of any withdrawal.

## 3. Opt-out

- Every marketing SMS needs a free and simple way to stop further messages.
- **"Reply STOP" does not work with an alphanumeric sender name** (`MyShop`): recipients cannot reply to it, and TopSMS does not process STOP replies. Put a short unsubscribe link, an e-mail address or a phone number in the text, for example `Abmelden: myshop.de/sms-stop` or `Odhlaseni: myshop.cz/stop`.
- Where TopSMS enforces opt-outs:
  - **Dashboard campaigns** and **calendar reminders** skip contacts marked as opted out (contact detail, or a CSV import with an `optOut` column).
  - **REST API, MCP, n8n, Make, plugins, HTTP GET, e-mail to SMS** do not read your contact list. They only reject numbers on the TopSMS blacklist. **Your code must keep its own suppression list and check it before every marketing send.**
- Process opt-outs immediately and permanently; do not send a "you have unsubscribed" marketing SMS.
- The `errorCode` `repeated_failure` (three failed deliveries to a number within 90 days) is a good signal to stop sending to that number as well.

## 4. When to send

- No law cited in TopSMS documentation sets SMS quiet hours, but night-time marketing annoys people and drives opt-outs. A common rule is to send marketing only between 08:00 and 20:00 in the **recipient's** time zone (the window TopSMS recommends in its own campaign-timing guide).
- The TopSMS calendar reminder feature enforces 21:00-08:00 itself. For your own sends, schedule with `send_at` (time zone required, max 30 days ahead) and compute the window per recipient country.
- Transactional messages (OTP, delivery updates) are expected immediately and can be sent at any time.

## 5. Identify the sender

Commercial communication must make the sender recognisable (in Germany § 6 para. 1 DDG; § 7 para. 2 no. 3 lit. a UWG treats concealed sender identity as an unreasonable nuisance). Send marketing under your real company name as sender ID (`topsms-send-sms`, sender rules) and link to a page with your imprint. TopSMS blocks sender names that resemble banks, carriers, authorities and other brands without a manual review.

## 6. GDPR basics

- A phone number is personal data. Each SMS needs a legal basis under Art. 6(1) GDPR: contract (b) for transactional messages, legitimate interest (f) possibly for security messages, consent (a) in practice for marketing.
- Inform people at collection (Art. 13), name your SMS gateway as a recipient (processor), keep numbers only as long as needed (Art. 5(1)(e)), honour objections to direct marketing at any time (Art. 21(2)), record the processing (Art. 30). Consent must be as easy to withdraw as to give (Art. 7(3)).
- The SMS gateway is a **processor**; Art. 28 GDPR requires a data processing agreement. TopSMS publishes its DPA, which applies to every account: https://topsms.eu/dpa (EN), https://topsms.eu/de/avv (DE), https://www.topsms.cz/zpracovatelska-smlouva (CZ). Per TopSMS's own documentation the application and database run in an EU data centre and delivery goes through EU-based carriers.
- Do not put more personal data into SMS texts than needed (no full addresses, health details or passwords). Message texts are stored in the message history.
- Never log OTP codes or API secrets.

## 7. Checklist for generated code

- [ ] Message type (transactional or marketing) decided per template; no promotion inside transactional texts
- [ ] Marketing: consent record checked before sending; double opt-in via the Verify API
- [ ] Own suppression list checked before every API marketing send
- [ ] Opt-out link, e-mail or phone in every marketing SMS (not "reply STOP" with a sender name)
- [ ] Sending window in the recipient's time zone for marketing
- [ ] Real company sender name, imprint reachable
- [ ] DPA in place, privacy notice mentions SMS and the gateway, retention periods set

Further reading from TopSMS: https://topsms.eu/blog/sms-marketing-gdpr-germany (EN), https://topsms.eu/de/blog/sms-marketing-dsgvo-deutschland (DE), https://www.topsms.cz/blog/jak-se-prijemce-odhlasi-z-sms-opt-out (CZ).
