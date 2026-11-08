#!/usr/bin/env node
// Send one SMS with the TopSMS REST API (Node.js 18+, no dependencies).
//
// Usage:
//   export TOPSMS_CLIENT_ID=...  TOPSMS_SECRET=...   # use a TEST key while developing
//   node send_sms.mjs +4915112345678 "Your order 1024 has shipped."
import { randomUUID } from 'node:crypto'

const BASE = (process.env.TOPSMS_BASE_URL || 'https://www.topsms.cz').replace(/\/$/, '')

export async function sendSms({ to, text, from, idempotencyKey = randomUUID() }) {
  const res = await fetch(`${BASE}/api/sms/send`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.TOPSMS_CLIENT_ID}:${process.env.TOPSMS_SECRET}`,
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey, // a retry with the same key never sends twice (24 h)
    },
    body: JSON.stringify(from ? { to, text, from } : { to, text }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(`TopSMS ${res.status} ${data.code ?? ''}: ${data.error ?? 'error'}`)
  return data // { ok, id, externalId, to, from, smsCount, price, status, currency, test? }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const [to, text] = process.argv.slice(2)
  if (!to || !text) {
    console.error('Usage: node send_sms.mjs <+E164 number> "<text>"')
    process.exit(2)
  }
  sendSms({ to, text }).then(r => console.log(JSON.stringify(r, null, 2))).catch(e => { console.error(e.message); process.exit(1) })
}
