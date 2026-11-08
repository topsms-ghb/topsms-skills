---
name: topsms-sms-length
description: Count SMS segments and cost exactly as TopSMS bills them - GSM-7 (160 characters, 153 per segment when longer) vs UCS-2 (70, 67 per segment), extension characters that count double (^ { } \ [ ~ ] | €), why German umlauts ä ö ü ß stay in GSM-7 while Czech/Slovak diacritics and typographic quotes or dashes switch the whole SMS to UCS-2, and how price = segments x price per destination. Use when writing SMS templates, estimating SMS cost, shortening texts, or when smsCount in a TopSMS response is higher than expected.
license: MIT
metadata:
  author: TopSMS
  version: "1.0.0"
---

# SMS length and segments (as TopSMS counts them)

TopSMS bills **segments**. The response field `smsCount` is the number of segments; `price` = `smsCount` x price per segment for the destination country. The count is decided by the encoding of the **whole** text.

## The rule

| Encoding | When | 1 segment | Each segment of a longer SMS |
|---|---|---|---|
| GSM-7 | every character is in the GSM 03.38 basic set or extension table | up to 160 | 153 |
| UCS-2 | at least one character is outside GSM-7 | up to 70 | 67 |

- GSM-7 length = number of characters, plus 1 for every **extension character** `^ { } \ [ ~ ] | €` (they take two septets).
- UCS-2 length = number of UTF-16 code units. Most emoji count as **2**.
- Segments = `1` if length <= single limit, otherwise `ceil(length / multi limit)`. Empty text = 0 (the API rejects it).

So 160 GSM characters = 1 SMS, 161 = 2 SMS (2 x 153 = 306 fit), 307 = 3 SMS. With one `č` or one emoji, 70 = 1 SMS, 71 = 2 SMS, 135 = 3 SMS.

## The GSM-7 basic set used by TopSMS

```
@ £ $ ¥ è é ù ì ò Ç LF Ø ø CR Å å Δ _ Φ Γ Λ Ω Π Ψ Σ Θ Ξ Æ æ ß É space ! " # ¤ % & ' ( ) * + , - . / 0-9 : ; < = > ? ¡ A-Z Ä Ö Ñ Ü § ¿ a-z ä ö ñ ü à
```

Extension (count as 2): `^ { } \ [ ~ ] | €`

Line breaks (LF, CR) are GSM-7. A tab is not.

## Language notes

- **German**: `ä ö ü Ä Ö Ü ß` are in GSM-7, so normal German text stays at 160/153. Do not strip umlauts; `Grüße` costs the same as `Gruesse` and reads better. The `€` sign counts as 2.
- **Czech and Slovak**: `á č ď ě í ň ó ř š ť ú ů ý ž`, `ľ ĺ ŕ ô` and their capitals are **not** GSM-7 (only `é`, `É` and `ä` are). A single one switches the SMS to UCS-2 (70/67). Many Czech senders write without diacritics (`Vase objednavka je na ceste`) to stay in 160; decide per use case.
- **French, Spanish, Italian, Nordic**: `é è à ù ì ò Ç Ñ ñ Å å Æ æ Ø ø` are in GSM-7; `ç` (lower case), `â ê î ô û ë ï œ á í ó ú` are not.
- **Typography from Word, websites and AI-written text** switches to UCS-2 silently: en/em dash `– —`, minus `−`, curly quotes `„ “ ” ‘ ’ « »`, ellipsis `…`, non-breaking and narrow spaces. Replace them with `- " ' ...` and a normal space.
- **Emoji** always mean UCS-2 and usually 2 units each.

When generating SMS text with an LLM, ask for plain ASCII punctuation and check the result with the script below before sending.

## Cost

Price per segment depends on the destination and the account (EUR for topsms.eu, CZK for topsms.cz). Current public prices: https://topsms.eu/pricing and https://topsms.eu/pricing.json (EU accounts), https://www.topsms.cz/cenik and https://www.topsms.cz/pricing.json (CZ accounts). Do not hard-code prices; read `price` from the send response or the pricing JSON (the MCP tool `get_pricing` returns it too).

Example (illustrative prices, check pricing.json): a German shipping notice of 140 GSM characters to `+49` = 1 segment. The same text with one `–` dash = UCS-2 = 140/67 = 3 segments, three times the price.

## Check a text before sending

[scripts/sms_length.py](scripts/sms_length.py) implements exactly the TopSMS algorithm (same character tables as the server) and also suggests a GSM-7-safe version:

```bash
python3 scripts/sms_length.py "Ihre Bestellung 1024 ist unterwegs – Grüße, MyShop"
# encoding=UCS-2 length=50 segments=1 limit=70/67 problem_chars=["–"]
# gsm7_version: Ihre Bestellung 1024 ist unterwegs - Grüße, MyShop  (GSM-7, 50, 1 segment)
```

The same check is available as a free web tool: https://topsms.eu/tools.

## Tips

- Put the important part first; long texts are joined on the phone but billed per segment.
- Placeholders are not filled by the API. Measure the final text after inserting names and order numbers; long names can push a text into a second segment.
- Links: count their full length. Use your own short domain rather than public shorteners.
