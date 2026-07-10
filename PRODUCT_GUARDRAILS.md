# Product guardrails

- Only structured seed-city selection is supported: continent → country/region → city.
- The user cannot submit free text, an IATA airport code, a place alias or an arbitrary address.
- Results distinguish protected tickets from separately purchased self-transfer tickets before expansion.
- Self-transfer, missed-connection, baggage and unknown transit requirements remain visible.
- Risk score is a decision aid, not legal, visa or operational advice.
- Mock prices are always identified as demo data. Redirect-only options are never confirmed prices.
- SplitFare does not promise lowest price, successful connection, baggage through-check or price stability.
- Booking requires canonical server-side option lookup and pre-redirect verification.
- No payment, ticketing, login, price alerts, scraping, CAPTCHA bypass or unauthorized OTA access.
- No production raw payload, stack trace, secret, credential-bearing URL or insecure external HTTP URL.
