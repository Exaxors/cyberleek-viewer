"""CYBERLEEK chain viewer — customtkinter GUI.

Reads everything straight from Solana mainnet RPC; no website dependency.
Sections mirror the site: MARKET / TOKEN / TRADE / LEEKS / POLL / ANNOUNCEMENTS / ABOUT.
"""

from __future__ import annotations

import queue
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import customtkinter as ctk

from cyberleek import (
    CONFIG_PDA,
    DECIMALS,
    MINT,
    RpcClient,
    fetch_all,
    format_amount,
    poll_tally,
    vote_address,
)

# ---------------------------------------------------------------- theme

C = {
    "bg": "#00050d",
    "card": "#00102b",
    "border": "#003299",
    "neon": "#0064ec",
    "green": "#60c33a",
    "red": "#ff3355",
    "amber": "#fbbf24",
    "text": "#a0b0c8",
    "bright": "#d6efc1",
    "dim": "#6a7a90",
    "dark": "#3a4a60",
}

FONT = ("Courier New", 12)
FONT_SM = ("Courier New", 11)
FONT_TINY = ("Courier New", 10)
FONT_BOLD = ("Courier New", 13, "bold")
FONT_TITLE = ("Courier New", 24, "bold")
FONT_HUGE = ("Courier New", 40, "bold")
FONT_LARGE = ("Courier New", 26, "bold")

AUTO_REFRESH_MS = 90_000

APP_VERSION = "20261011"
GITHUB_URL = "https://github.com/Exaxors/cyberleek-viewer"

ICON_PATH = Path(__file__).resolve().parent / "assets" / "icon.ico"


def short(pubkey: str) -> str:
    return pubkey[:8] + "..." + pubkey[-4:] if len(pubkey) > 16 else pubkey


def fmt_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def fmt_usd(v) -> str:
    if v is None:
        return "n/a"
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(v) >= limit:
            return f"${v / limit:,.2f}{suffix}"
    return f"${v:,.2f}"


def fmt_price(v) -> str:
    if v is None:
        return "n/a"
    return f"${v:,.4f}" if v >= 1 else "$" + f"{v:.8f}".rstrip("0")


def safe_url(url: str) -> bool:
    return url.lower().startswith(("http://", "https://", "magnet:"))


# ---------------------------------------------------------------- app


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("CYBERLEEK :: chain viewer")
        self.geometry("960x780")
        self.configure(fg_color=C["bg"])
        if ICON_PATH.exists():
            try:
                self.iconbitmap(str(ICON_PATH))
            except Exception:
                pass

        self.rpc = RpcClient()
        self.data = None
        self._busy = False
        self._closing = False
        self._q: "queue.Queue[object]" = queue.Queue()
        self._countdowns: list[tuple[ctk.CTkLabel, int]] = []

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        self.refresh()
        self.after(150, self._poll_queue)
        self.after(1000, self._tick_countdown)
        self.after(AUTO_REFRESH_MS, self._auto_refresh)

    # ------------------------------------------------------------ UI build

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=C["bg"])
        header.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            header, text="CYBERLEEK", font=FONT_TITLE, text_color=C["neon"]
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text="chain viewer · on-chain data · no website",
            font=FONT_SM,
            text_color=C["dim"],
        ).pack(side="left", padx=(14, 0), pady=(8, 0))
        self.btn_refresh = ctk.CTkButton(
            header,
            text="REFRESH",
            command=self.refresh,
            font=FONT_SM,
            fg_color=C["neon"],
            hover_color=C["border"],
            text_color="#00050d",
            width=110,
            height=30,
        )
        self.btn_refresh.pack(side="right")

        self.status = ctk.CTkLabel(self, text="connecting...", font=FONT_TINY, text_color=C["green"], anchor="w")
        self.status.pack(fill="x", padx=18)

        self.tabs = ctk.CTkTabview(self, fg_color=C["bg"])
        self.tabs.pack(fill="both", expand=True, padx=16, pady=6)
        for name in ("MARKET", "TOKEN", "TRADE", "LEEKS", "POLL", "ANNOUNCEMENTS", "ABOUT"):
            frame = self.tabs.add(name)
            frame.configure(fg_color=C["bg"])
        
        self.statusbar = ctk.CTkLabel(self, text="", font=FONT_TINY, text_color=C["dark"], anchor="w")
        self.statusbar.pack(fill="x", padx=18, pady=(0, 10))

    # ------------------------------------------------------------ refresh

    def refresh(self):
        if self._busy:
            return
        self._busy = True
        self.btn_refresh.configure(state="disabled", text="FETCHING...")
        self.status.configure(text="fetching on-chain state...", text_color=C["neon"])
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            result = fetch_all(self.rpc)
            tallies = []
            for poll in result["polls"]:
                try:
                    tallies.append(poll_tally(self.rpc, poll))
                except Exception:
                    tallies.append(([0] * len(poll["choices"]), 0))
            result["tallies"] = tallies
        except Exception as exc:  # noqa: BLE001
            result = exc
        self._q.put(result)

    def _poll_queue(self):
        try:
            while True:
                result = self._q.get_nowait()
                self._apply(result)
        except queue.Empty:
            pass
        if not self._closing:
            self.after(150, self._poll_queue)

    def _apply(self, result):
        self._busy = False
        self.btn_refresh.configure(state="normal", text="REFRESH")
        if isinstance(result, Exception):
            self.status.configure(text=f"ERROR: {result}", text_color=C["red"])
            return
        self.data = result
        self.status.configure(text="system online", text_color=C["green"])
        if not getattr(self, "_tab_initialized", False):
            self.tabs.set("ANNOUNCEMENTS")
            self._tab_initialized = True
        self._render_market()
        self._render_token()
        self._render_trade()
        self._render_leeks()
        self._render_poll()
        self._render_announcements()
        self._render_about()
        n_content = len(result["content"])
        n_polls = len(result["polls"])
        n_ann = len(result.get("announcements", []))
        mcap = fmt_usd((result.get("market") or {}).get("market_cap"))
        self.statusbar.configure(
            text=f"RPC: {result['rpc']}  |  config: {short(result['config']['authority'])}  |  "
            f"mcap {mcap}  |  {n_content} leeks  |  {n_polls} poll(s)  |  {n_ann} announcement(s)  |  updated {fmt_ts(int(datetime.now(timezone.utc).timestamp()))}"
        )

    def _auto_refresh(self):
        if not self._closing:
            if not self._busy:
                self.refresh()
            self.after(AUTO_REFRESH_MS, self._auto_refresh)

    def _tick_countdown(self):
        if not self._closing:
            now = int(datetime.now(timezone.utc).timestamp())
            for label, ends_at in self._countdowns:
                left = ends_at - now
                if left > 0:
                    d, rem = divmod(left, 86400)
                    h, rem = divmod(rem, 3600)
                    m, s = divmod(rem, 60)
                    label.configure(text=f"ends in {d}d {h:02d}h {m:02d}m {s:02d}s")
                else:
                    label.configure(text="finalizing...")
            self.after(1000, self._tick_countdown)

    def _on_close(self):
        self._closing = True
        try:
            self.rpc.close()
        finally:
            self.destroy()

    # ------------------------------------------------------------ helpers

    def _clear(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def _copy(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.configure(text="copied to clipboard", text_color=C["green"])

    def _open(self, url: str):
        if safe_url(url):
            webbrowser.open(url)

    # ------------------------------------------------------------ tabs

    def _render_market(self):
        tab = self.tabs.tab("MARKET")
        self._clear(tab)
        wrap = ctk.CTkScrollableFrame(tab, fg_color=C["bg"])
        wrap.pack(fill="both", expand=True)

        ctk.CTkLabel(wrap, text="◈ MARKET (DexScreener, off-chain)", font=FONT_BOLD, text_color=C["green"]).pack(anchor="w", pady=(8, 4))
        market = self.data.get("market")
        if not market:
            ctk.CTkLabel(
                wrap, text="market data unavailable (price service not reachable)",
                font=("Courier New", 16), text_color=C["dim"],
            ).pack(anchor="w", pady=12)
            return

        def card(parent, label, value, color, font):
            box = ctk.CTkFrame(parent, fg_color=C["card"], border_width=1, border_color=C["border"])
            ctk.CTkLabel(box, text=label.upper(), font=FONT_SM, text_color=C["dim"]).pack(anchor="w", padx=16, pady=(12, 0))
            ctk.CTkLabel(box, text=value, font=font, text_color=color).pack(anchor="w", padx=16, pady=(2, 14))
            return box

        card(wrap, "Market cap", fmt_usd(market.get("market_cap")), C["bright"], FONT_HUGE).pack(fill="x", pady=4)
        card(wrap, "Price", fmt_price(market.get("price_usd")), C["bright"], FONT_HUGE).pack(fill="x", pady=4)

        chg = market.get("change_24h")
        if chg is None:
            chg_text, chg_color = "n/a", C["bright"]
        else:
            chg_text, chg_color = f"{chg:+.2f}%", (C["green"] if chg >= 0 else C["red"])
        cells = [
            ("Liquidity", fmt_usd(market.get("liquidity_usd")), C["bright"]),
            ("24h volume", fmt_usd(market.get("volume_24h")), C["bright"]),
            ("24h change", chg_text, chg_color),
        ]
        grid = ctk.CTkFrame(wrap, fg_color=C["bg"])
        grid.pack(fill="x", pady=4)
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1, uniform="market")
        for col, (label, value, color) in enumerate(cells):
            card(grid, label, value, color, FONT_LARGE).grid(
                row=0, column=col, sticky="nsew",
                padx=(0 if col == 0 else 4, 0 if col == 2 else 4),
            )

        src = "source: DexScreener" + (f"  ·  pair on {market['dex']}" if market.get("dex") else "")
        ctk.CTkLabel(wrap, text=src, font=FONT_TINY, text_color=C["dim"]).pack(anchor="w", pady=(10, 2))
        url = market.get("url") or ""
        if safe_url(url):
            ctk.CTkButton(
                wrap, text="OPEN ON DEXSCREENER →", font=FONT_SM,
                fg_color=C["neon"], hover_color=C["border"], text_color="#00050d",
                command=lambda u=url: self._open(u),
            ).pack(anchor="w", pady=(2, 10))

    def _render_token(self):
        tab = self.tabs.tab("TOKEN")
        self._clear(tab)
        wrap = ctk.CTkScrollableFrame(tab, fg_color=C["bg"])
        wrap.pack(fill="both", expand=True)

        ctk.CTkLabel(wrap, text="◈ CONTRACT ADDRESS", font=FONT_BOLD, text_color=C["green"]).pack(anchor="w", pady=(8, 4))
        ca_row = ctk.CTkFrame(wrap, fg_color=C["card"], border_width=1, border_color=C["border"])
        ca_row.pack(fill="x")
        ctk.CTkLabel(ca_row, text=MINT, font=FONT_SM, text_color=C["neon"], wraplength=600, justify="left").pack(side="left", padx=12, pady=10)
        ctk.CTkButton(ca_row, text="COPY", width=80, font=FONT_TINY, fg_color=C["neon"], hover_color=C["border"], text_color="#00050d", command=lambda: self._copy(MINT)).pack(side="right", padx=10)

        info = self.data["mint_info"] or {}
        ctk.CTkLabel(wrap, text="◈ MINT ACCOUNT (on-chain, jsonParsed)", font=FONT_BOLD, text_color=C["green"]).pack(anchor="w", pady=(16, 4))
        rows = [
            ("Supply", f"{format_amount(int(info.get('supply', 0)))} (raw {info.get('supply', 0)})"),
            ("Decimals", str(info.get("decimals", DECIMALS))),
            ("Mint authority", "REVOKED ✓" if info.get("mintAuthority") is None else str(info["mintAuthority"])),
            ("Freeze authority", "REVOKED ✓" if info.get("freezeAuthority") is None else str(info["freezeAuthority"])),
            ("Initialized", str(info.get("isInitialized", False))),
        ]
        for label, value in rows:
            row = ctk.CTkFrame(wrap, fg_color=C["card"], border_width=1, border_color=C["border"])
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label.upper(), font=FONT_TINY, text_color=C["dim"], width=180, anchor="w").pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(row, text=value, font=FONT_SM, text_color=C["bright"], anchor="w").pack(side="left", padx=12, pady=8)

        ctk.CTkLabel(wrap, text="◈ SITE CLAIMS (static HTML, not chain-verified)", font=FONT_BOLD, text_color=C["green"]).pack(anchor="w", pady=(16, 4))
        claims = ctk.CTkFrame(wrap, fg_color=C["card"], border_width=1, border_color=C["border"])
        claims.pack(fill="x")
        ctk.CTkLabel(
            claims,
            text="LP Burned ✓\nMint Revoked ✓ (confirmed on-chain)\nFreeze Revoked ✓ (confirmed on-chain)\nBuy tax 0% · Sell tax 0%",
            font=FONT_SM, text_color=C["text"], justify="left",
        ).pack(anchor="w", padx=12, pady=10)

    def _render_trade(self):
        tab = self.tabs.tab("TRADE")
        self._clear(tab)
        wrap = ctk.CTkScrollableFrame(tab, fg_color=C["bg"])
        wrap.pack(fill="both", expand=True)

        swaps = [s for s in (self.data["config"] or {}).get("swap_links", []) if s.get("enabled")]
        if not swaps:
            ctk.CTkLabel(wrap, text="no trade links on-chain", font=FONT, text_color=C["dim"]).pack(anchor="w", pady=8)
            return
        for s in swaps:
            url = s["url"].replace("{MINT}", MINT)
            row = ctk.CTkFrame(wrap, fg_color=C["card"], border_width=1, border_color=C["border"])
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=f"◈ {s['name']}", font=FONT_BOLD, text_color=C["green"], width=180, anchor="w").pack(side="left", padx=12, pady=12)
            ctk.CTkLabel(row, text=url, font=FONT_TINY, text_color=C["dim"], anchor="w").pack(side="left", padx=8, pady=12)
            ctk.CTkButton(row, text="OPEN", width=80, font=FONT_TINY, fg_color=C["neon"], hover_color=C["border"], text_color="#00050d", command=lambda u=url: self._open(u)).pack(side="right", padx=10)

    def _render_leeks(self):
        tab = self.tabs.tab("LEEKS")
        self._clear(tab)
        wrap = ctk.CTkScrollableFrame(tab, fg_color=C["bg"])
        wrap.pack(fill="both", expand=True)

        posts = self.data["content"]
        if not posts:
            ctk.CTkLabel(wrap, text="no content accounts on-chain", font=FONT, text_color=C["dim"]).pack(anchor="w", pady=8)
            return

        for post in posts:
            card = ctk.CTkFrame(wrap, fg_color=C["card"], border_width=1, border_color=C["border"])
            card.pack(fill="x", pady=5)
            ctk.CTkLabel(
                card,
                text=f"◈ {post['title'].upper()}",
                font=("Courier New", 14, "bold"),
                text_color=C["neon"],
                wraplength=820,
                justify="left",
            ).pack(anchor="w", padx=12, pady=(10, 2))
            ctk.CTkLabel(
                card,
                text=f"{fmt_ts(post['timestamp'])}  ·  by {short(post['authority'])}  ·  acct {post['account']}",
                font=FONT_TINY,
                text_color=C["dim"],
                wraplength=820,
                justify="left",
            ).pack(anchor="w", padx=12, pady=(0, 6))
            for item in post["items"]:
                url = item["url"]
                ok = safe_url(url)
                is_magnet = url.lower().startswith("magnet:")
                row = ctk.CTkFrame(card, fg_color=C["bg"])
                row.pack(fill="x", padx=10, pady=2)
                color = C["green"] if is_magnet else C["neon"]
                ctk.CTkLabel(
                    row,
                    text=f"▸ {item['label'][:44]}",
                    font=FONT_SM,
                    text_color=color,
                    anchor="w",
                    width=320,
                ).pack(side="left", padx=8, pady=6)
                ctk.CTkLabel(row, text=url, font=FONT_TINY, text_color=C["dim"], anchor="w").pack(side="left", padx=8, pady=6)
                ctk.CTkButton(
                    row, text="OPEN", width=62, font=FONT_TINY, height=24,
                    fg_color=color, hover_color=C["border"], text_color="#00050d",
                    state="normal" if ok else "disabled",
                    command=lambda u=url: self._open(u),
                ).pack(side="right", padx=4)
                ctk.CTkButton(
                    row, text="COPY", width=62, font=FONT_TINY, height=24,
                    fg_color="transparent", hover_color=C["border"], text_color=color,
                    border_width=1, border_color=color,
                    command=lambda u=url: self._copy(u),
                ).pack(side="right", padx=4)

    def _render_poll(self):
        tab = self.tabs.tab("POLL")
        self._clear(tab)
        wrap = ctk.CTkScrollableFrame(tab, fg_color=C["bg"])
        wrap.pack(fill="both", expand=True)

        self._countdowns = []
        polls = self.data["polls"]
        if not polls:
            ctk.CTkLabel(wrap, text="no poll accounts on-chain", font=FONT, text_color=C["dim"]).pack(anchor="w", pady=8)
            return

        now = int(datetime.now(timezone.utc).timestamp())
        tallies = self.data.get("tallies", [])
        for idx, poll in enumerate(polls):
            tally = tallies[idx] if idx < len(tallies) else ([0] * len(poll["choices"]), 0)
            # Alterado para True em todos os polls para mostrar os detalhes e percentagens em todos
            self._render_poll_card(wrap, poll, now, tally, detailed=True)

    def _render_poll_card(self, wrap, poll, now, tally, detailed):
        card = ctk.CTkFrame(wrap, fg_color=C["card"], border_width=1, border_color=C["border"])
        card.pack(fill="x", pady=5)

        balances, total = tally

        is_live = now < poll["ends_at"] and not all(poll["is_finalized"])
        badge = "◈ LIVE" if is_live else "◈ ENDED"
        badge_color = C["green"] if is_live else C["red"]

        ctk.CTkLabel(card, text=f"{badge}  {poll['title']}", font=FONT_BOLD, text_color=C["bright"], wraplength=820, justify="left").pack(anchor="w", padx=12, pady=(10, 2))
        meta = f"ends {fmt_ts(poll['ends_at'])}" if is_live else f"ended {fmt_ts(poll['ends_at'])}"
        meta += f"  ·  {format_amount(total)} $CYBERLEEK donated"
        ctk.CTkLabel(card, text=meta, font=FONT_TINY, text_color=C["dim"]).pack(anchor="w", padx=12, pady=(0, 4))

        if is_live:
            cd = ctk.CTkLabel(card, text="", font=FONT_TINY, text_color=C["green"])
            cd.pack(anchor="w", padx=12)
            self._countdowns.append((cd, poll["ends_at"]))

        if not detailed:
            return

        leading_idx = max(range(len(balances)), key=lambda i: balances[i]) if total > 0 else 0
        for i, choice in enumerate(poll["choices"]):
            bal = balances[i] if i < len(balances) else 0
            pct = (bal * 100.0 / total) if total > 0 else 0.0
            winner = i == leading_idx and total > 0
            row = ctk.CTkFrame(card, fg_color=C["bg"], border_width=1, border_color=C["green"] if winner else C["border"])
            row.pack(fill="x", padx=10, pady=3)
            name_color = C["green"] if winner else C["bright"]
            ctk.CTkLabel(row, text=f"{'★ ' if winner else ''}{choice}", font=FONT_SM, text_color=name_color, width=240, anchor="w").pack(side="left", padx=10, pady=(8, 2))
            ctk.CTkLabel(row, text=f"{format_amount(bal)}  ({pct:.1f}%)", font=FONT_SM, text_color=C["green"] if winner else C["text"]).pack(side="right", padx=10, pady=(8, 2))
            bar = ctk.CTkProgressBar(row, fg_color=C["border"], progress_color=C["green"] if winner else C["neon"], height=5, corner_radius=0)
            bar.pack(fill="x", padx=10, pady=(0, 4))
            bar.set(max(pct / 100.0, 0.005) if total > 0 else 0.0)
            addr = vote_address(poll["poll_id"], i)
            foot = ctk.CTkFrame(row, fg_color=C["bg"])
            foot.pack(fill="x", padx=10, pady=(0, 6))
            ctk.CTkLabel(foot, text=f"vote addr: {addr}", font=FONT_TINY, text_color=C["dark"], anchor="w").pack(side="left")
            ctk.CTkButton(foot, text="COPY", width=62, height=22, font=FONT_TINY, fg_color="transparent", hover_color=C["border"], text_color=C["dim"], border_width=1, border_color=C["border"], command=lambda a=addr: self._copy(a)).pack(side="right")

        ctk.CTkLabel(
            card,
            text="HOW VOTING WORKS: send $CYBERLEEK to a choice's vote address. Only $CYBERLEEK is accepted — "
            "sending SOL or other tokens results in loss of funds. Donations are final.",
            font=FONT_TINY, text_color=C["dim"], wraplength=840, justify="left",
        ).pack(anchor="w", padx=12, pady=(6, 10))

    def _render_announcements(self):
        tab = self.tabs.tab("ANNOUNCEMENTS")
        self._clear(tab)
        wrap = ctk.CTkScrollableFrame(tab, fg_color=C["bg"])
        wrap.pack(fill="both", expand=True)

        items = self.data.get("announcements", [])
        if not items:
            ctk.CTkLabel(wrap, text="no announcement accounts on-chain", font=FONT, text_color=C["dim"]).pack(anchor="w", pady=8)
            return

        for ann in items:
            card = ctk.CTkFrame(wrap, fg_color=C["card"], border_width=1, border_color=C["border"])
            card.pack(fill="x", pady=5)
            ctk.CTkLabel(
                card, text=f"◈ {ann['title']}", font=("Courier New", 14, "bold"),
                text_color=C["neon"], wraplength=820, justify="left",
            ).pack(anchor="w", padx=12, pady=(10, 2))
            ctk.CTkLabel(
                card,
                text=f"{fmt_ts(ann['timestamp'])}  ·  by {short(ann['authority'])}  ·  acct {ann['account']}",
                font=FONT_TINY, text_color=C["dim"], wraplength=820, justify="left",
            ).pack(anchor="w", padx=12, pady=(0, 6))
            ctk.CTkLabel(
                card, text=ann["body"], font=FONT_SM, text_color=C["text"],
                wraplength=820, justify="left",
            ).pack(anchor="w", padx=12, pady=(0, 8))
            ctk.CTkButton(
                card, text="COPY", width=62, height=22, font=FONT_TINY,
                fg_color="transparent", hover_color=C["border"], text_color=C["dim"],
                border_width=1, border_color=C["border"],
                command=lambda a=ann: self._copy(f"{a['title']}\n\n{a['body']}"),
            ).pack(anchor="e", padx=12, pady=(0, 10))

    def _render_about(self):
        tab = self.tabs.tab("ABOUT")
        self._clear(tab)
        wrap = ctk.CTkScrollableFrame(tab, fg_color=C["bg"])
        wrap.pack(fill="both", expand=True)

        ctk.CTkLabel(wrap, text="CYBERLEEKVIEWER", font=("Courier New", 22, "bold"), text_color=C["neon"]).pack(anchor="w", pady=(8, 2))
        ctk.CTkLabel(wrap, text=f"v{APP_VERSION}  ·  by n0ne, Exaxors", font=FONT_SM, text_color=C["dim"]).pack(anchor="w")
        ctk.CTkLabel(
            wrap,
            text="A desktop chain viewer for the CYBERLEEK site — reads everything straight from "
            "Solana mainnet RPC. No website, no backend, no wallet connect.",
            font=FONT_SM, text_color=C["text"], wraplength=840, justify="left",
        ).pack(anchor="w", pady=(4, 10))
        ctk.CTkButton(
            wrap, text="View on GitHub →", font=FONT_SM,
            fg_color=C["neon"], hover_color=C["border"], text_color="#00050d",
            command=lambda: self._open(GITHUB_URL),
        ).pack(anchor="w", pady=(0, 14))

        cfg = self.data["config"] or {}
        about = (cfg.get("about") or "").strip()
        mission = (cfg.get("mission") or "").strip()

        ctk.CTkLabel(wrap, text="◈ ON-CHAIN CONFIG", font=FONT_BOLD, text_color=C["green"]).pack(anchor="w", pady=(8, 4))
        ctk.CTkLabel(
            wrap,
            text=f"config PDA: {CONFIG_PDA}\n"
            f"authority:  {cfg.get('authority', '?')}\n"
            f"section flags: " + ", ".join(f"{s['id']}={s['visible']}" for s in cfg.get("sections", [])),
            font=FONT_SM, text_color=C["text"], justify="left",
        ).pack(anchor="w", pady=4)

        ctk.CTkLabel(wrap, text="◈ ABOUT (on-chain)", font=FONT_BOLD, text_color=C["green"]).pack(anchor="w", pady=(16, 4))
        if not about:
            about = "No about text has been published."
        box = ctk.CTkTextbox(wrap, font=FONT_SM, text_color=C["text"], fg_color=C["card"], border_width=1, border_color=C["border"], wrap="word", height=220)
        box.pack(fill="x")
        box.insert("1.0", about)
        box.configure(state="disabled")

        ctk.CTkLabel(wrap, text="◈ MISSION (on-chain)", font=FONT_BOLD, text_color=C["green"]).pack(anchor="w", pady=(16, 4))
        if not mission:
            mission = "No mission text has been published."
        box2 = ctk.CTkTextbox(wrap, font=FONT_SM, text_color=C["text"], fg_color=C["card"], border_width=1, border_color=C["border"], wrap="word", height=120)
        box2.pack(fill="x")
        box2.insert("1.0", mission)
        box2.configure(state="disabled")

        faq = cfg.get("faq") or []
        if faq:
            ctk.CTkLabel(wrap, text="◈ FAQ (on-chain)", font=FONT_BOLD, text_color=C["green"]).pack(anchor="w", pady=(16, 4))
            for qa in faq:
                ctk.CTkLabel(wrap, text=f"Q: {qa['question']}\nA: {qa['answer']}", font=FONT_SM, text_color=C["text"], wraplength=840, justify="left").pack(anchor="w", pady=4)

        contact = cfg.get("contact") or []
        if contact:
            ctk.CTkLabel(wrap, text="◈ CONTACT (on-chain)", font=FONT_BOLD, text_color=C["green"]).pack(anchor="w", pady=(16, 4))
            for c in contact:
                row = ctk.CTkFrame(wrap, fg_color=C["card"], border_width=1, border_color=C["border"])
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=f"◈ {c['platform']}", font=FONT_BOLD, text_color=C["green"], width=180, anchor="w").pack(side="left", padx=12, pady=8)
                ctk.CTkLabel(row, text=c["url"], font=FONT_TINY, text_color=C["dim"], anchor="w").pack(side="left", padx=8, pady=8)
                ctk.CTkButton(row, text="OPEN", width=80, font=FONT_TINY, fg_color=C["neon"], hover_color=C["border"], text_color="#00050d", command=lambda u=c["url"]: self._open(u)).pack(side="right", padx=10)


if __name__ == "__main__":
    App().mainloop()
