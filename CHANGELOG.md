# Changelog

This is a fork of [ZeroHackz/cyberleek-viewer](https://github.com/ZeroHackz/cyberleek-viewer).
Versions use the date format of the original (`YYYYMMDD`).

## [20261011] - 2026-10-11

### Added
- **ANNOUNCEMENTS tab** – shows the announcements Cyberleek now publishes on-chain
  (title, timestamp, author, account, full text, copy button), newest first.
  - New decoder `decode_announcement()` for the announcement account type
    (discriminator `NjkxTouaByo`; layout: 8 B discriminator, pubkey, i64 timestamp,
    string title, string body, zero padding).
  - Announcements are queried by discriminator only, without a fixed `dataSize`
    filter, so a change of the padded account size does not hide them.
- **MARKET tab** (first tab) – market cap, price, liquidity, 24h volume and 24h change
  with large, easy-to-read numbers, plus an "Open on DexScreener" button.
  - Data comes from the free DexScreener API (off-chain, no API key). It refreshes
    together with everything else (every 90 s or on REFRESH).
  - Only pairs whose base token is exactly the CYBERLEEK mint on Solana are used,
    so look-alike tokens with the same name cannot appear. The most liquid pair wins.
  - If the first endpoint fails a second one is tried; if the API provides no market
    cap it is computed from price × on-chain supply.
  - If the price service is unreachable the tab says so and the on-chain refresh
    still works normally.
- Status bar now also shows the current market cap and the announcement count.
- New app and executable icon (`assets/icon.ico`).
- `RpcClient.get_json()` helper for the off-chain price request.

### Changed
- About page: version updated to `v20261011`, author line changed to `by n0ne`.
- Default selected tab on first load is now **ANNOUNCEMENTS**.
- `RpcClient.get_program_accounts()` – `data_size` is now optional.
- TOKEN tab no longer contains market data (moved to the MARKET tab).
- Tab order: `MARKET, TOKEN, TRADE, LEEKS, POLL, ANNOUNCEMENTS, ABOUT`.

### Earlier changes already present in this fork
*(carried over from the working copy; check against `git diff` before publishing)*
- Poll tally treats a poll as finished only when **all** options are finalized.
- Vote options without a token account yet (0 votes) are counted as 0 instead of raising an error.
- `python cyberleek.py` prints poll results with vote amounts and percentages.
- Poll cards show details and percentages for every poll.

## Credits
Original project and on-chain decoding by [ZeroHackz](https://github.com/ZeroHackz/cyberleek-viewer).