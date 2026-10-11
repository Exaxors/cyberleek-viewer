# CyberleekViewer

A desktop **chain viewer** for the CYBERLEEK site, built with Python + customtkinter.
It reads everything straight from **Solana mainnet RPC** — no website, no browser,
no backend, no wallet connect. The only off-chain request is the optional price lookup
for the MARKET tab (DexScreener's public API).

> **Fork notice:** this is a maintained fork of
> [ZeroHackz/cyberleek-viewer](https://github.com/ZeroHackz/cyberleek-viewer), which is no longer
> updated. All credit for the original project and the on-chain decoding goes to ZeroHackz.
> See the [CHANGELOG](CHANGELOG.md) for what this fork adds.

<img width="399" height="399" alt="cinema" src="https://github.com/user-attachments/assets/3e11aa89-f697-42ad-a2e4-5b9a8e16b65c" />

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

1. Go to the [**Releases**](https://github.com/<your-username>/cyberleek-viewer/releases) page,
   download the latest `CyberleekViewer.zip`, extract it, and run
   `CyberleekViewer\CyberleekViewer.exe` — no Python or dependencies needed.
   Keep the whole extracted folder together; the exe needs the files next to it.
2. Run the application. It fetches on-chain state automatically on startup.
3. Pick a tab:
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
   git clone https://github.com/<your-username>/cyberleek-viewer.git
   cd cyberleek-viewer
   ```
2. First run — `launcher.bat` creates the virtual environment, installs
   dependencies, and starts the app.
3. To build the portable executable:
   ```bat
   build.bat
   ```
   The app folder lands in `dist\CyberleekViewer\` and is zipped to `dist\CyberleekViewer.zip`.
4. Enjoy the view.

## Project layout

```
cyberleek-viewer/
  app.py             # customtkinter GUI
  cyberleek.py       # RPC client + on-chain decoders + market lookup (no UI deps)
  make_icon.py       # icon generator
  cyberleek.spec     # PyInstaller spec
  launcher.bat       # first-run setup + launch (no console window)
  build.bat          # builds dist\CyberleekViewer\ + auto-zips it
  smoke.py           # headless GUI smoke test
  requirements.txt
  CHANGELOG.md       # what changed in this fork
  assets/icon.ico    # app + exe icon
  screenshots/
  dist/              # build output (git-ignored, released via GitHub Releases)
```

## ⚖️ Disclaimer

- **No Affiliation**: This project and its authors are not affiliated,
  associated, authorized, endorsed by, or in any way officially connected with
  Rockstar Games, Take-Two Interactive, Cyberleek, or any of their subsidiaries
  or affiliates.
- **Educational & Research Purposes Only**: This is an independent viewer
  provided solely for educational research into decentralized publishing
  patterns; it only reads public on-chain data.
- **Market Data**: Prices and market caps in the MARKET tab come from DexScreener's public API.
  They are informational only, may be delayed or inaccurate, and are not financial advice.
- **Content Responsibility**: The authors do not host, stream, generate, or
  claim ownership of any third-party media, leaked content, or intellectual
  property. All product names, logos, brands, and media mentioned or displayed
  belong to their respective copyright holders.
- **Use at Your Own Risk**: Software is provided "as is", without warranty of
  any kind. You are solely responsible for ensuring compliance with your local
  laws and host provider terms of service.
