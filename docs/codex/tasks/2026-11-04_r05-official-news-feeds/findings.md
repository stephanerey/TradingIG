# Findings

- The Federal Reserve publishes official RSS feeds, including monetary-policy releases at
  `https://www.federalreserve.gov/feeds/press_monetary.xml`.
- The ECB publishes an official press/news RSS at `https://www.ecb.europa.eu/rss/press.html`.
- Both feeds returned HTTP 200 during the bounded 2026-11-04 format probe.
- The BLS documents `https://www.bls.gov/schedule/news_release/bls.ics`, but the live automated
  probe returned Access Denied and an anti-bot notice. It is excluded rather than bypassed.
- RSS payloads provide publication metadata but no calibrated market impact; importance must remain
  unknown until an authorized deterministic or AI assessment layer supplies evidence.
- Fed live payload: HTTP 200, RSS 2.0 metadata, 15 normalized monetary-policy items.
- ECB live payload: HTTP 200, RSS 2.0 metadata, 15 normalized press/news items.
- Both live adapters passed the same HTTPS host, timestamp, content-type and metadata-only checks as
  synthetic fixtures.
