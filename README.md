# TopSMS Agent Skills

Agent Skills that teach coding agents the [TopSMS](https://topsms.eu) SMS API, packaged as a Claude Code plugin that also connects the official TopSMS remote MCP server.

**Skills are knowledge, MCP is action.** The skills tell an agent how the API really behaves: request and response shapes, limits, sender rules, webhook signatures, segment counting and compliance, so the code it writes works the first time. The MCP server lets the agent send an SMS, check delivery or credit right now. One plugin install gives you both.

TopSMS is a prepaid SMS gateway: [topsms.eu](https://topsms.eu) for Germany, Austria and the EU (EUR), [topsms.cz](https://www.topsms.cz) for Czechia and Slovakia (CZK). Same API for both.

## Skills

| Skill | What the agent learns |
|---|---|
| [`topsms-getting-started`](skills/topsms-getting-started/SKILL.md) | Accounts (EUR vs CZK), API keys `Bearer clientId:secret`, scopes, test keys, base URL, first SMS in curl / Python / Node.js / PHP, error codes |
| [`topsms-send-sms`](skills/topsms-send-sms/SKILL.md) | Single and bulk sending (500 per request, queue above 50), `send_at` scheduling and cancellation, `Idempotency-Key`, sender name rules, links rule, E.164 phone numbers |
| [`topsms-delivery-reports`](skills/topsms-delivery-reports/SKILL.md) | Status endpoint, statuses and `errorCode`, webhook payload, `X-TopSMS-Signature` HMAC-SHA256 verification, retry schedule |
| [`topsms-otp-verify`](skills/topsms-otp-verify/SKILL.md) | Verify API send/check, limits, test codes, OTP security practice |
| [`topsms-sms-length`](skills/topsms-sms-length/SKILL.md) | GSM-7 vs UCS-2, 160/153 and 70/67, double-counted characters, German umlauts vs Czech diacritics, cost per segment |
| [`topsms-integrations`](skills/topsms-integrations/SKILL.md) | Remote MCP server and its 9 tools, n8n node, Make app, shop plugins, HTTP GET API, e-mail to SMS, calendar reminders, PHP library |
| [`topsms-compliance`](skills/topsms-compliance/SKILL.md) | Transactional vs marketing, consent and double opt-in, opt-out handling, sending hours, GDPR and the DPA (general information, not legal advice) |

Each skill is a folder with a `SKILL.md` (YAML frontmatter `name` and `description`, then instructions) following the open [Agent Skills](https://agentskills.io/specification) format, plus small runnable scripts where useful (Python standard library, Node.js 18+ without dependencies, PHP with curl).

## Install

### Claude Code: plugin (skills + MCP server)

```text
/plugin marketplace add topsms-ghb/topsms-skills
/plugin install topsms@topsms
```

or from your shell:

```bash
claude plugin marketplace add topsms-ghb/topsms-skills
claude plugin install topsms@topsms
```

This installs the seven skills and registers the remote MCP server `https://topsms.eu/api/mcp` (from [`.mcp.json`](.mcp.json)). Run `/mcp` in Claude Code and sign in to your TopSMS account to authorise it. Skills are namespaced by the plugin, for example `topsms:topsms-send-sms`.

Accounts from www.topsms.cz can use the server as is (sign-in works for both sites); if you prefer, add `https://www.topsms.cz/api/mcp` yourself with `claude mcp add --transport http topsms https://www.topsms.cz/api/mcp`.

### Claude Code: skills only

```bash
git clone https://github.com/topsms-ghb/topsms-skills.git
mkdir -p ~/.claude/skills
cp -R topsms-skills/skills/* ~/.claude/skills/
```

Use `.claude/skills/` inside a project instead of `~/.claude/skills/` to share the skills with your team through the repository. Add the MCP server separately if you want it:

```bash
claude mcp add --transport http topsms https://topsms.eu/api/mcp
```

### Other agents

The skills are plain folders with a `SKILL.md`. Copy `skills/<name>/` into the skills directory of any agent that supports the Agent Skills format, or point an agent that reads Markdown instructions (for example via `AGENTS.md` or project rules) at the `SKILL.md` files. The MCP server works with any client that supports remote MCP over Streamable HTTP, with OAuth sign-in or the header `Authorization: Bearer <clientId>:<secret>`; setup for claude.ai, ChatGPT, Cursor and others: [topsms.eu/mcp](https://topsms.eu/mcp).

## Try it safely

Create a **test key** in the dashboard ([www.topsms.cz/dashboard/api](https://www.topsms.cz/dashboard/api), tick "test key"). It sends and charges nothing, returns real response shapes and simulated delivery reports. Every script in this repository reads `TOPSMS_CLIENT_ID` and `TOPSMS_SECRET` from the environment:

```bash
export TOPSMS_CLIENT_ID=...  TOPSMS_SECRET=...
python3 skills/topsms-getting-started/scripts/send_sms.py +4915112345678 "Hello from TopSMS"
python3 skills/topsms-sms-length/scripts/sms_length.py "Grüße aus Berlin – bis morgen"
```

No secrets are stored in this repository. Never commit API keys or webhook secrets.

## Documentation

- REST API: [topsms.eu/docs](https://topsms.eu/docs) (EN), [topsms.eu/de/docs](https://topsms.eu/de/docs) (DE), [www.topsms.cz/api-integrace/rest-api](https://www.topsms.cz/api-integrace/rest-api) (CZ)
- OpenAPI: [topsms.eu/openapi.yaml](https://topsms.eu/openapi.yaml)
- For LLMs: [topsms.eu/llms.txt](https://topsms.eu/llms.txt), [topsms.eu/llms-full.txt](https://topsms.eu/llms-full.txt)
- MCP server: [topsms.eu/mcp](https://topsms.eu/mcp), npm package [`topsms-mcp`](https://www.npmjs.com/package/topsms-mcp)
- SMS for AI agents: [topsms.eu/ai](https://topsms.eu/ai), [topsms.eu/de/ki](https://topsms.eu/de/ki), [www.topsms.cz/ai](https://www.topsms.cz/ai)
- Privacy: [topsms.eu/privacy-policy](https://topsms.eu/privacy-policy) · Terms: [topsms.eu/terms](https://topsms.eu/terms) · DPA: [topsms.eu/dpa](https://topsms.eu/dpa)

## Contributing

Issues and pull requests are welcome. Keep every statement true to the live API: if behaviour changes, update the skill and its examples together.

## License

[MIT](LICENSE) © TopSMS, info@topsms.eu
