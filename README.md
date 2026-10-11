# CyberleekViewer

A desktop **chain viewer** for the CYBERLEEK site, built with Python + customtkinter.
It reads everything straight from **Solana mainnet RPC** — no website, no browser,
no backend, no wallet connect. The only off-chain request is the optional price lookup
for the MARKET tab (DexScreener's public API).

> **Fork notice:** this is a maintained fork of
> [ZeroHackz/cyberleek-viewer](https://github.com/ZeroHackz/cyberleek-viewer), which is no longer
> actively maintained. All credit for the original project goes to ZeroHackz.
> See the [CHANGELOG](CHANGELOG.md) for what this fork adds.

<img width="399" height="399" alt="teabag" src="screenshots/teabag.gif" />

## Screenshots

*Main UI: token info, trade links, and the on-chain LEEKS list with mirrors.*

![Main UI](screenshots/MAIN_UI.png)

*Poll tab: live vote bars from token balances, vote addresses, countdown.*

![Poll tab](screenshots/POLLS_TAB_UI.png)

*Market tab: market cap, price, liquidity, 24h volume and change in large type.*

![Market tab](screenshots/MARKET_TAB_UI.png)

*Announcements tab: the announcements Cyberleek publishes on-chain.*

![Announcements tab](screenshots/ANNOUNCEMENTS_TAB_UI.png)

## ✨ Features

- **MARKET** tab — market cap, price, liquidity, 24h volume and 24h change in large, easy-to-read
  numbers, with a button to open the live chart on DexScreener. Only the real CYBERLEEK mint is
  matched, so look-alike tokens with the same name never show up. If the price service is
  unreachable, the tab says so and everything else keeps working.
- **TOKEN** tab — live mint account from the chain (supply, decimals, mint/freeze authority —
  revocation confirmed on-chain).
- **TRADE** tab — swap links (Raydium, DexScreener, Birdeye, defined) straight from the on-chain config.
- **LEEKS** tab — every content account sorted by timestamp.
- **POLL** tab — vote bars and percentages computed from real token-account balances for every poll,
  running or ended. Running polls show a countdown; finished polls use the finalized on-chain
  balances; options that have no votes yet correctly show 0.
- **ANNOUNCEMENTS** tab — the announcements published on-chain, newest first, with title, time,
  author, full text and a copy button.
- **ABOUT** tab — on-chain about/mission/FAQ/contact and section flags.
- **Status bar** — active RPC, current market cap, and counts of leeks, polls and announcements.
- **Auto-refresh** every 90 s (or hit REFRESH).
- **Portable Windows executable** — `dist\CyberleekViewer\CyberleekViewer.exe`, no Python needed.

## 💻 How to Use (Easy Way)

1. Go to the [**Releases**](https://github.com/Exaxors/cyberleek-viewer/releases) page,
   download the latest `CyberleekViewer.zip`, extract it, and run
   `CyberleekViewer\CyberleekViewer.exe` — no Python or dependencies needed.
   Keep the whole extracted folder together; the exe needs the files next to it.
2. Run the application. It fetches on-chain state automatically on startup.
3. On first launch the app opens on the **ANNOUNCEMENTS** tab. Pick any tab:
   * **MARKET** — current market cap and price.
   * **TOKEN** — check the mint account.
   * **TRADE** — check a swap link.
   * **LEEKS** — on-chain URLs.
   * **POLL** — watch live voting.
   * **ANNOUNCEMENTS** — read the latest announcements.
   * **ABOUT** — read the on-chain config.
4. That's it. Data refreshes automatically; the status bar shows everything.

> **Windows SmartScreen:** the exe is not code-signed, so Windows (or your antivirus) may warn
> about it. Choose *More info → Run anyway* if you trust the download, or build it yourself from
> source (below). Each release lists the SHA-256 of the zip so you can verify your download with
> `Get-FileHash CyberleekViewer.zip`.

## 🛠️ For Developers (Building from Source)

1. Install Python 3.10+ (tested with 3.13) and get the project:
   ```bash
   git clone https://github.com/Exaxors/cyberleek-viewer.git
   cd cyberleek-viewer