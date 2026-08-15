#!/usr/bin/env python3
"""Watch a cross-chain price spread via LI.FI /v1/token (CoinGecko priceUSD).

This is a READ-ONLY research signal: it compares the CoinGecko `priceUSD` of
the same asset on two chains and raises a flag when the paper spread exceeds a
threshold. It does NOT sign, authorize, or broadcast anything.

Why paper spread only:
  `priceUSD` is a CoinGecko estimate, not a fillable price. A triggered spread
  still needs a `/v1/quote` (or `advanced/routes`) check against a real pool /
  order book before it means anything executable. Use a conservative threshold.

Designed for repeated runs (e.g. cron): it always prints a one-line result and
can emit a full JSON document for long-term drift analysis.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


API = "https://li.quest/v1/token"


def fetch_token(chain: int, token: str) -> dict[str, Any]:
    url = f"{API}?chain={chain}&token={token}"
    req = urllib.request.Request(
        url, headers={"user-agent": "onchain-arbitrage-colearning/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(errors="replace"), file=sys.stderr)
        raise


def price_usd(token: dict[str, Any]) -> float:
    raw = token.get("priceUSD")
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--chain-a", type=int, required=True, help="First chain id")
    p.add_argument("--chain-b", type=int, required=True, help="Second chain id")
    p.add_argument("--token-a", required=True, help="Token address on chain A")
    p.add_argument("--token-b", required=True, help="Token address on chain B")
    p.add_argument("--threshold", type=float, default=0.5,
                   help="Spread percent that triggers a flag (default 0.5%%)")
    p.add_argument("--json-output", type=Path, help="Optional JSON document path")
    args = p.parse_args()

    ta = fetch_token(args.chain_a, args.token_a)
    tb = fetch_token(args.chain_b, args.token_b)

    pa, pb = price_usd(ta), price_usd(tb)
    sym_a = ta.get("symbol", "?")
    sym_b = tb.get("symbol", "?")
    ver_a = ta.get("verificationStatus", "unknown")
    ver_b = tb.get("verificationStatus", "unknown")

    # Same-asset sanity check: comparing different symbols is usually a mistake
    # (e.g. USDC vs USDC.e). Warn rather than silently produce a fake spread.
    mismatch = sym_a != sym_b

    if pa > 0 and pb > 0:
        low, high = min(pa, pb), max(pa, pb)
        spread_pct = (high - low) / low * 100.0
    else:
        spread_pct = 0.0

    triggered = (not mismatch) and spread_pct >= args.threshold

    document = {
        "queried_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": API,
        "pair": [
            {"chain": args.chain_a, "token": args.token_a, "symbol": sym_a,
             "price_usd": pa, "verified": ver_a},
            {"chain": args.chain_b, "token": args.token_b, "symbol": sym_b,
             "price_usd": pb, "verified": ver_b},
        ],
        "spread_pct": round(spread_pct, 6),
        "threshold_pct": args.threshold,
        "triggered": triggered,
        "symbol_mismatch": mismatch,
        "note": "paper spread from CoinGecko priceUSD; not a fillable price",
    }

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        )

    if mismatch:
        print(
            f"WARN symbol mismatch {sym_a}(chain {args.chain_a}) vs "
            f"{sym_b}(chain {args.chain_b}) — spread not computed"
        )
        return 3

    line = (
        f"{document['queried_at_utc']} {sym_a}: chain {args.chain_a}=${pa:.4f} "
        f"chain {args.chain_b}=${pb:.4f} spread={spread_pct:.3f}% "
        f"threshold={args.threshold}% "
        f"{'TRIGGERED' if triggered else 'ok'}"
    )
    print(line)
    return 1 if triggered else 0


if __name__ == "__main__":
    raise SystemExit(main())
