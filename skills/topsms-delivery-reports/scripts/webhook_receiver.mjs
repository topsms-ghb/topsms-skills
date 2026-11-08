#!/usr/bin/env node
// Minimal TopSMS delivery-report webhook receiver (Node.js 18+, no dependencies).
//
//   export TOPSMS_WEBHOOK_SECRET=...   # shown once when you set the webhook URL on the API key
//   node webhook_receiver.mjs 8080
//
// With Express use express.raw({ type: 'application/json' }) on this route and pass req.body (a Buffer)
// to verifyTopSmsSignature: the HMAC is computed over the raw body, not over re-serialised JSON.
import { createHmac, timingSafeEqual } from 'node:crypto'
import { createServer } from 'node:http'

export function verifyTopSmsSignature(rawBody, header, secret) {
  if (!secret || typeof header !== 'string' || !header.startsWith('sha256=')) return false
  const expected = Buffer.from(createHmac('sha256', secret).update(rawBody).digest('hex'))
  const given = Buffer.from(header.slice(7))
  return expected.length === given.length && timingSafeEqual(expected, given)
}

const SECRET = process.env.TOPSMS_WEBHOOK_SECRET
const seen = new Set() // use your database in production

if (import.meta.url === `file://${process.argv[1]}`) {
  if (!SECRET) { console.error('Set TOPSMS_WEBHOOK_SECRET'); process.exit(2) }
  const port = Number(process.argv[2] || 8080)
  createServer((req, res) => {
    if (req.method !== 'POST') { res.writeHead(405).end(); return }
    const chunks = []
    req.on('data', c => chunks.push(c))
    req.on('end', () => {
      const raw = Buffer.concat(chunks)
      if (!verifyTopSmsSignature(raw, req.headers['x-topsms-signature'], SECRET)) { res.writeHead(401).end(); return }
      const ev = JSON.parse(raw.toString('utf8'))
      const key = `${ev.id}:${ev.status}`
      if (!seen.has(key)) { // idempotent processing
        seen.add(key)
        console.log(ev.status, ev.to, `id=${ev.id}`, `errorCode=${ev.errorCode}`, `test=${!!ev.test}`)
      }
      res.writeHead(204).end() // any 2xx within 5 s
    })
  }).listen(port, () => console.log(`listening on :${port}`))
}
