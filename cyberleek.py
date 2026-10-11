"""CYBERLEEK on-chain data client.

Talks directly to Solana mainnet RPC endpoints — no website, no browser.
Replicates exactly the queries the site's JS bundle performs:

  * config   -> getAccountInfo(frontend_config PDA) + decode
  * content  -> getProgramAccounts(memcmp "G6JNBZ2BSey", dataSize 7156) + decode
  * polls    -> getProgramAccounts(memcmp "5Qpj1hsHT4k", dataSize 2800) + decode
  * announcements -> getProgramAccounts(memcmp "NjkxTouaByo") + decode
  * votes    -> PDA(["option", pollId, [idx]]) -> ATA PDA, token balances
"""

from __future__ import annotations

import base64
import random
import struct
from typing import Optional

import httpx
from solders.pubkey import Pubkey

# ---------------------------------------------------------------- constants

ANCHOR = "7rAgHPLDc9NryZmNdeEzyDui6D9PHkvTxMjKhNSa7w3a"
MINT = "ApZuxdpzMrbEYTGEzeY9afh5pj9d6qPRJCTgQYiipbKg"
DECIMALS = 9

CONFIG_SEED = b"frontend_config"
CONFIG_PDA = "Eq19BaJAbuxiH8JtL1pX7F8bwVnPVK5vdmhZQ7KAi8cA"
CONTENT_DISCRIMINATOR = "G6JNBZ2BSey"
CONTENT_DATA_SIZE = 7156
POLL_DISCRIMINATOR = "5Qpj1hsHT4k"
POLL_DATA_SIZE = 2800
# off-chain price source (free, no API key): used only for the market cap display
MARKET_URLS = [
    "https://api.dexscreener.com/latest/dex/tokens/" + MINT,
    "https://api.dexscreener.com/token-pairs/v1/solana/" + MINT,
]
ANNOUNCEMENT_DISCRIMINATOR = "NjkxTouaByo"  # accounts are zero-padded to 656 B; no size filter needed

TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ATA_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")

RPC_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana.api.onfinality.io/public",
    "https://public.rpc.solanavibestation.com",
    "https://solana.api.pocket.network",
    "https://solana-rpc.publicnode.com",
    "https://solana-mainnet.gateway.tatum.io",
]

_anchor = Pubkey.from_string(ANCHOR)
_mint = Pubkey.from_string(MINT)

_config_pda, _config_bump = Pubkey.find_program_address([CONFIG_SEED], _anchor)
assert str(_config_pda) == CONFIG_PDA, "config PDA derivation mismatch"


# ---------------------------------------------------------------- decoders


class Reader:
    """Little-endian binary reader, mirrors the JS `te` class."""

    __slots__ = ("buf", "pos")

    def __init__(self, buf: bytes):
        self.buf = buf
        self.pos = 0

    def rem(self) -> int:
        return len(self.buf) - self.pos

    def seek(self, p: int) -> None:
        self.pos = p

    def u8(self) -> int:
        v = self.buf[self.pos]
        self.pos += 1
        return v

    def u32(self) -> int:
        (v,) = struct.unpack_from("<I", self.buf, self.pos)
        self.pos += 4
        return v

    def u64(self) -> int:
        (v,) = struct.unpack_from("<Q", self.buf, self.pos)
        self.pos += 8
        return v

    def i64(self) -> int:
        (v,) = struct.unpack_from("<q", self.buf, self.pos)
        self.pos += 8
        return v

    def raw(self, n: int) -> bytes:
        v = self.buf[self.pos : self.pos + n]
        self.pos += n
        return v

    def pubkey(self) -> str:
        return str(Pubkey.from_bytes(self.raw(32)))

    def string(self) -> str:
        n = self.u32()
        return self.raw(n).decode("utf-8", "replace")

    def boolean(self) -> bool:
        return self.u8() != 0


def decode_content(raw: bytes) -> Optional[dict]:
    """8-byte discriminator | pubkey | i64 ts | str title | vec<str label, str url>."""
    try:
        t = Reader(raw[8:])
        authority = t.pubkey()
        timestamp = t.i64()
        title = t.string()
        save = t.pos
        try:
            count = t.u32()
            items = []
            for _ in range(count):
                label = t.string()
                url = t.string()
                items.append({"label": label, "url": url})
        except Exception:
            t.seek(save)
            url = t.string()
            items = [{"label": url, "url": url}]
        return {"authority": authority, "timestamp": timestamp, "title": title, "items": items}
    except Exception:
        return None


def decode_announcement(raw: bytes) -> Optional[dict]:
    """8B discriminator | pubkey | i64 ts | str title | str body | zero padding."""
    try:
        t = Reader(raw[8:])
        authority = t.pubkey()
        timestamp = t.i64()
        title = t.string()
        body = t.string()
        return {"authority": authority, "timestamp": timestamp, "title": title, "body": body}
    except Exception:
        return None


def decode_poll(raw: bytes) -> Optional[dict]:
    """8B discriminator | pubkey | i64 ts | 32B pollId | str title |
    vec<str> choices | i64 endsAt | vec<bool> finalized | vec<u64> finalBalances?"""
    try:
        t = Reader(raw[8:])
        authority = t.pubkey()
        timestamp = t.i64()
        poll_id = t.raw(32)
        title = t.string()
        count = t.u32()
        choices = [t.string() for _ in range(count)]
        ends_at = t.i64()
        count = t.u32()
        finalized = [t.boolean() for _ in range(count)]
        balances: list[int] = []
        if t.rem() >= 4:
            try:
                count = t.u32()
                balances = [t.u64() for _ in range(count)]
            except Exception:
                balances = []
        return {
            "authority": authority,
            "timestamp": timestamp,
            "poll_id": poll_id,
            "title": title,
            "choices": choices,
            "ends_at": ends_at,
            "is_finalized": finalized,
            "final_balances": balances,
        }
    except Exception:
        return None


def decode_config(raw: bytes) -> Optional[dict]:
    """8B discriminator | pubkey | str about | str mission | vec<q,a> faq |
    vec<platform,url> contact | vec<name,url,bool> swapLinks | vec sections."""
    try:
        t = Reader(raw[8:])
        authority = t.pubkey()
        about = t.string()
        mission = t.string()
        count = t.u32()
        faq = [{"question": t.string(), "answer": t.string()} for _ in range(count)]
        count = t.u32()
        contact = [{"platform": t.string(), "url": t.string()} for _ in range(count)]
        count = t.u32()
        swaps = [{"name": t.string(), "url": t.string(), "enabled": t.boolean()} for _ in range(count)]
        count = t.u32()
        sections = [
            {"id": t.string(), "visible": t.boolean(), "state": t.string(), "order": t.u8()}
            for _ in range(count)
        ]
        return {
            "authority": authority,
            "about": about,
            "mission": mission,
            "faq": faq,
            "contact": contact,
            "swap_links": swaps,
            "sections": sections,
        }
    except Exception:
        return None


# ---------------------------------------------------------------- RPC


class RpcError(RuntimeError):
    pass


class RpcClient:
    def __init__(self, endpoints: Optional[list[str]] = None, timeout: float = 8.0):
        self.endpoints = list(endpoints or RPC_ENDPOINTS)
        self.timeout = timeout
        self.active: Optional[str] = None
        self._http = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def _pool(self) -> list[str]:
        eps = list(self.endpoints)
        random.shuffle(eps)
        if self.active:
            eps.insert(0, self.active)
        return eps

    def call(self, method: str, params: list) -> object:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        last: Optional[Exception] = None
        for ep in self._pool():
            try:
                r = self._http.post(ep, json=payload)
                r.raise_for_status()
                data = r.json()
                if "error" in data:
                    raise RpcError(str(data["error"].get("message", "rpc error")))
                self.active = ep
                return data.get("result")
            except Exception as exc:  # noqa: BLE001
                last = exc
        raise RpcError(f"all RPC endpoints failed: {last}")

    def healthy(self, endpoint: str) -> bool:
        try:
            return self.call("getSlot", []) is not None
        except Exception:
            return False

    def get_account_info(self, pubkey: str) -> Optional[bytes]:
        result = self.call("getAccountInfo", [pubkey, {"encoding": "base64"}])
        value = (result or {}).get("value")  # type: ignore[union-attr]
        if not value:
            return None
        return base64.b64decode(value["data"][0])

    def get_program_accounts(self, memcmp: str, data_size: Optional[int] = None) -> list[tuple[str, bytes]]:
        filters: list[dict] = [{"memcmp": {"offset": 0, "bytes": memcmp}}]
        if data_size is not None:
            filters.append({"dataSize": data_size})
        result = self.call("getProgramAccounts", [ANCHOR, {"encoding": "base64", "filters": filters}])
        out: list[tuple[str, bytes]] = []
        for acc in result or []:  # type: ignore[union-attr]
            out.append((acc["pubkey"], base64.b64decode(acc["account"]["data"][0])))
        return out

    def get_token_balance(self, pubkey: str) -> int:
        try:
            result = self.call("getTokenAccountBalance", [pubkey])
            value = (result or {}).get("value")  # type: ignore[union-attr]
            if not value:
                return 0
            return int(value["amount"])
        except Exception:
            #se a conta de tokens ainda nao existir (ex: opcao com 0 votos), 
            #o RPC devolve erro. apanhamos a excecao e assumimos 0.
            return 0

    def get_json(self, url: str) -> object:
        r = self._http.get(url)
        r.raise_for_status()
        return r.json()

    def get_mint_info(self) -> Optional[dict]:
        result = self.call("getAccountInfo", [MINT, {"encoding": "jsonParsed"}])
        value = (result or {}).get("value")  # type: ignore[union-attr]
        if not value:
            return None
        return value["data"]["parsed"]["info"]


# ---------------------------------------------------------------- helpers


def vote_address(poll_id: bytes, choice_index: int) -> str:
    """Replicates se(pollId, idx) from the site:
    option PDA = findPDA(["option", pollId, [idx]], anchor)
    vote addr  = findPDA([optionPda, TOKEN_PROGRAM, mint], ATA program)"""
    option_pda, _ = Pubkey.find_program_address(
        [b"option", poll_id, bytes([choice_index])], _anchor
    )
    ata, _ = Pubkey.find_program_address(
        [bytes(option_pda), bytes(TOKEN_PROGRAM), bytes(_mint)], ATA_PROGRAM
    )
    return str(ata)


def format_amount(raw: int, decimals: int = DECIMALS) -> str:
    whole, rem = divmod(raw, 10**decimals)
    s = f"{whole:,}"
    if rem:
        frac = str(rem).zfill(decimals).rstrip("0")
        if frac:
            s += "." + frac
    return s


def _num(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def fetch_market(rpc: RpcClient, supply: Optional[float] = None) -> Optional[dict]:
    """Price / market cap for MINT from DexScreener (off-chain). Returns None on any failure.

    Only pairs whose *base token is exactly MINT* on Solana are used, so look-alike
    tokens with the same name can never leak in. The most liquid pair wins."""
    for url in MARKET_URLS:
        try:
            data = rpc.get_json(url)
        except Exception:
            continue
        pairs = data.get("pairs") if isinstance(data, dict) else data
        best, best_liq = None, -1.0
        for p in pairs or []:
            if not isinstance(p, dict):
                continue
            if p.get("chainId") != "solana" or (p.get("baseToken") or {}).get("address") != MINT:
                continue
            liq = _num((p.get("liquidity") or {}).get("usd")) or 0.0
            if liq > best_liq:
                best, best_liq = p, liq
        if best is None:
            continue
        price = _num(best.get("priceUsd"))
        mcap = _num(best.get("marketCap")) or _num(best.get("fdv"))
        if mcap is None and price is not None and supply:
            mcap = price * supply
        return {
            "price_usd": price,
            "market_cap": mcap,
            "liquidity_usd": best_liq if best_liq >= 0 else None,
            "volume_24h": _num((best.get("volume") or {}).get("h24")),
            "change_24h": _num((best.get("priceChange") or {}).get("h24")),
            "dex": best.get("dexId"),
            "url": best.get("url"),
        }
    return None


def poll_tally(rpc: RpcClient, poll: dict) -> tuple[list[int], int]:
    """Per-choice balances + total. Uses on-chain final balances when the poll
    is fully finalized, otherwise reads live token-account balances."""
    n = len(poll["choices"])
    
    # usar all() para garantir que TODAS as opções estão finalized
    if all(poll["is_finalized"]) and poll.get("final_balances"):
        balances = poll["final_balances"][:n]
    else:
        balances = []
        for i in range(n):
            try:
                # tenta ir buscar o saldo em tempo real à rede Solana
                bal = rpc.get_token_balance(vote_address(poll["poll_id"], i))
                balances.append(bal)
            except Exception:
                # se der erro (ex: a conta de tokens da opção ainda não existe porque tem 0 votos), assume 0
                balances.append(0)
                
    return balances, sum(balances)


def fetch_all(rpc: Optional[RpcClient] = None) -> dict:
    """One call that grabs everything the site renders."""
    own = rpc is None
    rpc = rpc or RpcClient()
    try:
        config_raw = rpc.get_account_info(CONFIG_PDA)
        config = decode_config(config_raw) if config_raw else None

        content: list[dict] = []
        for pk, raw in rpc.get_program_accounts(CONTENT_DISCRIMINATOR, CONTENT_DATA_SIZE):
            item = decode_content(raw)
            if item:
                item["account"] = pk
                content.append(item)
        content.sort(key=lambda x: x["timestamp"], reverse=True)

        polls: list[dict] = []
        for pk, raw in rpc.get_program_accounts(POLL_DISCRIMINATOR, POLL_DATA_SIZE):
            poll = decode_poll(raw)
            if poll:
                poll["account"] = pk
                polls.append(poll)
        polls.sort(key=lambda x: x["timestamp"], reverse=True)

        announcements: list[dict] = []
        for pk, raw in rpc.get_program_accounts(ANNOUNCEMENT_DISCRIMINATOR):
            ann = decode_announcement(raw)
            if ann:
                ann["account"] = pk
                announcements.append(ann)
        announcements.sort(key=lambda x: x["timestamp"], reverse=True)

        mint_info = rpc.get_mint_info()

        market = None
        try:
            supply = int((mint_info or {}).get("supply", 0)) / 10 ** int((mint_info or {}).get("decimals", DECIMALS))
            market = fetch_market(rpc, supply or None)
        except Exception:
            market = None  # price service down must never break the on-chain refresh

        return {
            "rpc": rpc.active,
            "config": config,
            "content": content,
            "polls": polls,
            "announcements": announcements,
            "mint_info": mint_info,
            "market": market,
        }
    finally:
        if own:
            rpc.close()


if __name__ == "__main__":
    import json

    # instanciar o RPC Client aqui para poder usá-lo no poll_tally
    rpc = RpcClient()
    try:
        data = fetch_all(rpc)
        
        # processar as votações (polls) para incluir as percentagens
        polls_output = []
        for poll in data["polls"]:
            # buscar os saldos de cada opção e o total de votos
            balances, total = poll_tally(rpc, poll)
            
            choices_data = []
            for idx, choice in enumerate(poll["choices"]):
                balance = balances[idx] if idx < len(balances) else 0
                
                # calcula a percentagem, protegendo contra divisão por zero
                percentage = (balance / total * 100) if total > 0 else 0.0
                
                choices_data.append({
                    "choice": choice,
                    "votes": format_amount(balance),
                    "percentage": f"{percentage:.1f}%"
                })
            
            polls_output.append({
                "title": poll["title"],
                "status": "ENDED" if poll.get("is_finalized") and all(poll["is_finalized"]) else "LIVE",
                "total_donated": format_amount(total),
                "options": choices_data
            })

        # imprimir o JSON final com os novos dados
        print(json.dumps(
            {
                "rpc": data["rpc"],
                "poll_count": len(data["polls"]),
                "polls": polls_output,
            },
            indent=2,
        ))
    finally:
        rpc.close()