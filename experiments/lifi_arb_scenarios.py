#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LI.FI 套利场景示例代码
========================
每个场景一个函数 + 一个"简单例子"注释块。
只用标准库(urllib/json)，零依赖，可直接跑。

已验证的 LI.FI API 事实(2026-08 实测)：
- 公开 GET 接口： https://li.quest/v1/...
- /v1/token?chain=1&token=<addr>      -> 单个 token 元数据 + priceUSD + verificationStatus  (200 ✓)
- /v1/tokens?chains=1,42161,8453      -> 批量 token 元数据                                (200 ✓)
- /v1/quote?fromChain=&toChain=...    -> 报价/单条 route                                 (200 ✓, fromAddress 不能为 0 地址)
- /v1/advanced/routes (POST)          -> 多候选 route 比较(生产环境, 通常需要 integrator key)

报价返回 estimate 字段(实测 shape):
  estimate.toAmount / toAmountMin / fromAmountUSD / toAmountUSD / executionDuration
  estimate.feeCosts[]   (name, amount, token.symbol)
  estimate.gasCosts[]   (估计 gas 费)
  transactionRequest    (value, to, data, chainId, gasPrice, gasLimit, from)
"""

import json
import urllib.request
import urllib.parse

API = "https://li.quest/v1"
UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# ---- 常用 token 地址(仅作演示, 用 /v1/token 校验为准) ----
ETH = "0x0000000000000000000000000000000000000000"
USDC_ETH = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"      # Ethereum 原生 USDC
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"     # Base 原生 USDC
USDC_ARB = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"      # Arbitrum 原生 USDC
USDCe_ARB = "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8"     # Arbitrum bridged USDC.e (易混淆!)

CHAINS = {"ethereum": 1, "arbitrum": 42161, "base": 8453}


def _get(path, **params):
    url = API + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def fmt_usd(usd_str):
    try:
        return float(usd_str)
    except (TypeError, ValueError):
        return 0.0


# =====================================================================
# 场景 1: 跨链套利 —— 必须把跨链耗时算进去
# ---------------------------------------------------------------------
# 简单例子:
#   Arbitrum 上 ETH 折合 $1855, Base 上 ETH $1866, 看起来有 ~0.6% 价差。
#   但跨链桥从发起 -> 目标链到账 -> 再 swap, 动辄 1~10 分钟。
#   Quote 显示"盈利"是静态快照, 不代表资产到账时价差还在。
#   正确做法: 两端都预先备好资金, 各自在本链吃价差, 之后用 LI.FI 做库存再平衡。
# =====================================================================
def check_crosschain_spread(token_symbol_hint=None, chains=("arbitrum", "base")):
    """对比同一 token 在不同链的 priceUSD(CoinGecko 口径), 看纸面价差。"""
    print("== 场景1: 跨链纸面价差检测 ==")
    ids = ",".join(str(CHAINS[c]) for c in chains)
    data = _get("/tokens", chains=ids)
    prices = {}
    for chain_id, tokens in data["tokens"].items():
        for t in tokens:
            if t.get("symbol") == "ETH":  # 演示用 ETH, 换成任意 token 同理
                prices[chain_id] = (t["symbol"], float(t["priceUSD"]))
    for cid, (sym, p) in prices.items():
        print(f"  chain {cid}: {sym} = ${p}")
    if len(prices) == 2:
        ps = list(prices.values())
        spread = (max(p[1] for p in ps) - min(p[1] for p in ps)) / min(p[1] for p in ps) * 100
        print(f"  纸面价差: {spread:.3f}%  (注意: 未扣跨链耗时/桥费/gas, 不可直接套)")
    return prices


def quote_crosschain(from_chain="arbitrum", to_chain="base", from_token=ETH,
                     to_token=ETH, from_amount=1_000_000_000_000_000_000, addr="0x" + "0" * 39 + "1"):
    """拿到跨链 route 的真实成本: 到账金额、耗时、桥费。"""
    print("== 场景1: 跨链 route 成本拆解 ==")
    d = _get("/quote", fromChain=CHAINS[from_chain], toChain=CHAINS[to_chain],
             fromToken=from_token, toToken=to_token, fromAmount=from_amount, fromAddress=addr)
    est = d["estimate"]
    fees = sum(float(f.get("amount", 0)) for f in est.get("feeCosts", []))
    print(f"  tool       : {d.get('tool')}")
    print(f"  toAmountMin: {est.get('toAmountMin')}  (slippage 后保底到账)")
    print(f"  executionDuration: {est.get('executionDuration')}s")
    print(f"  feeCosts   : {fees}")
    # 关键结论: 若 executionDuration 很大, 或桥非原子, 则 quote 盈利是幻觉
    return d


# =====================================================================
# 场景 2: Token Price 与 Token Service —— 先辨清地址/decimals/版本
# ---------------------------------------------------------------------
# 简单例子:
#   "USDC" 在 Arbitrum 上有原生 USDC(0xaf88...) 和桥接 USDC.e(0xFF97...)。
#   两者价格/流动性/认可度不同, 若把 USDC.e 当成 USDC, 后续价差比较全部失真。
#   /v1/token 返回 metadata + priceUSD + verificationStatus。
# =====================================================================
def resolve_token(chain, address):
    """确认 token 身份, 避免 USDC/USDC.e/Wrapped 混淆。"""
    print(f"== 场景2: token 身份校验 (chain={chain}) ==")
    t = _get("/token", chain=CHAINS[chain], token=address)
    print(f"  symbol   : {t.get('symbol')}")
    print(f"  name     : {t.get('name')}")
    print(f"  decimals : {t.get('decimals')}")
    print(f"  priceUSD : {t.get('priceUSD')}")
    print(f"  verified : {t.get('verificationStatus')}")  # verified / unknown / rejected
    return t


# =====================================================================
# 场景 3: Route 比较与同链 Swap —— 输出最多 != 最优
# ---------------------------------------------------------------------
# 简单例子:
#   同链 ETH->USDC 可能有多条 route: Uniswap 直换 / 经聚合器多跳 / 走 Curve 稳定池。
#   输出最多的 route 可能更慢、步骤更多、失败后恢复更麻烦。
#   应比较 toAmountMin(而非 toAmount, 因为它没算 slippage)、gas、fee、duration、tool 风险。
# =====================================================================
def compare_samechain_routes(chain="ethereum", from_token=ETH, to_token=USDC_ETH,
                             from_amount=1_000_000_000_000_000_000, addr="0x" + "0" * 39 + "1"):
    """生产上应调 /v1/advanced/routes(POST) 一次拿多候选; 这里用多次 /quote 演示比较维度。"""
    print("== 场景3: 同链 route 比较维度 ==")
    d = _get("/quote", fromChain=CHAINS[chain], toChain=CHAINS[chain],
             fromToken=from_token, toToken=to_token, fromAmount=from_amount, fromAddress=addr)
    est = d["estimate"]
    to_amount = float(est["toAmount"]) / 1e6  # USDC 6 decimals
    to_min = float(est["toAmountMin"]) / 1e6
    print(f"  tool       : {d.get('tool')}  (工具风险: DEX 聚合器 vs 单池)")
    print(f"  toAmount   : {to_amount:.2f} USDC")
    print(f"  toAmountMin: {to_min:.2f} USDC  <- 用这个比, 已含 slippage")
    print(f"  feeCosts   : {[(f.get('name'), f.get('amount')) for f in est.get('feeCosts', [])]}")
    print(f"  gasCosts   : {[(g.get('type'), g.get('amount')) for g in est.get('gasCosts', [])]}")
    print(f"  duration   : {est.get('executionDuration')}s")
    print(f"  步骤数     : {len(d.get('includedSteps', []))}")
    return d


# =====================================================================
# 场景 4: 多链库存再平衡 —— 把"抓机会"和"跨链调仓"拆开
# ---------------------------------------------------------------------
# 简单例子:
#   套利跑一段时间后, Base 上 USDC 越来越少(一直在吃 Base 侧价差),
#   Arbitrum 上 USDC 越堆越多。在不要求极低延迟的时段, 用 LI.FI 把
#   Arbitrum 的多余 USDC 调回 Base。这比"发现价差后临时跨链"更适合普通跨链工具。
# =====================================================================
def rebalance_inventory(current, target, from_chain="arbitrum", to_chain="base",
                        token=USDC_ARB, to_token=USDC_BASE, addr="0x" + "0" * 39 + "1"):
    """current: {chain: USDC余额}; target: {chain: 目标余额}; 算出该调多少并报价。"""
    print("== 场景4: 多链库存再平衡 ==")
    moves = {}
    for c in current:
        diff = current[c] - target.get(c, 0)
        if diff != 0:
            moves[c] = diff  # >0 需转出, <0 需转入
    print("  余额偏离:", {c: f"{v:+.2f}" for c, v in moves.items()})
    # 只演示从 from_chain 转出多余部分到 to_chain
    excess = current.get(from_chain, 0) - target.get(from_chain, 0)
    if excess <= 0:
        print("  无需调仓")
        return None
    raw = int(excess * 1e6)  # USDC 6 decimals
    d = _get("/quote", fromChain=CHAINS[from_chain], toChain=CHAINS[to_chain],
             fromToken=token, toToken=to_token, fromAmount=raw, fromAddress=addr)
    est = d["estimate"]
    print(f"  转出 {excess:.2f} USDC 从 {from_chain} -> {to_chain}")
    print(f"  到账保底: {float(est['toAmountMin'])/1e6:.2f} USDC")
    print(f"  耗时: {est.get('executionDuration')}s (调仓不抢时间, 可选桥费更低的慢 route)")
    return d


# =====================================================================
# 场景 5: Intents / Composer / Earn —— 套利之后资金去哪
# ---------------------------------------------------------------------
# 简单例子:
#   套利结束, 手里有闲置稳定币。用 Earn 发现收益机会;
#   用 Composer 把"跨链 + deposit/stake"打包成一笔交易;
#   Intents 则是让 Solver 围绕一个目标结果(如"给我在 Base 上拿到最多 USDC")竞争报价。
#   这些不直接等于套利策略, 但扩展了资金管理的后续动作。
# =====================================================================
def earn_discovery(chains="1,42161,8453"):
    """Earn: 发现收益机会(演示: 复用 /tokens 展示链上可配置资产)。"""
    print("== 场景5a: Earn 收益机会发现(示意) ==")
    # 生产上走 LI.FI Earn 专用接口(需 partner 权限)。这里展示思路。
    print("  套利结束后的闲置稳定币 -> 查询各链 lending/staking APY -> 调仓进入收益仓位")


def composer_deposit_flow(from_chain="arbitrum", to_chain="base", from_token=USDC_ARB,
                          to_token=USDC_BASE, from_amount=5_000_000_000, addr="0x" + "0" * 39 + "1"):
    """Composer: 跨链 + 后续协议调用(如 deposit)打包成一笔交易(需 integrator key)。"""
    print("== 场景5b: Composer 跨链后继续 deposit(示意) ==")
    # 生产上 POST /v1/advanced/stepTransactions 或 contractCall, 把
    # [bridge USDC] -> [deposit 进 Aave/Compound] 合成一次签名。
    print("  step1 bridge USDC(arb)->USDC(base), step2 deposit 进 lending 池, 单次签名原子执行")


def intent_request(target_chain="base", want_token=USDC_BASE):
    """Intents: 表达目标结果, 让 Solver 竞争执行(需 partner/auction 接入)。"""
    print("== 场景5c: Intents 目标表达(示意) ==")
    print(f"  目标: 在 chain {CHAINS[target_chain]} 拿到最多 {want_token[:10]}...")
    print("  多个 Solver 围绕该目标竞价, 选最优执行(更省 gas/更快到账)")


if __name__ == "__main__":
    print("=" * 70)
    print("LI.FI 套利场景示例(公开接口实测可跑)")
    print("=" * 70)

    # 场景 2 先跑, 因为要先把 token 身份认清楚(套利的第 0 步)
    resolve_token("arbitrum", USDC_ARB)
    print()
    resolve_token("arbitrum", USDCe_ARB)   # 对比: 桥接版, 别和上面搞混
    print()

    # 场景 1
    check_crosschain_spread()
    print()

    # 场景 3
    compare_samechain_routes()
    print()

    # 场景 4
    rebalance_inventory(
        current={"arbitrum": 10000.0, "base": 2000.0, "ethereum": 5000.0},
        target={"arbitrum": 6000.0, "base": 6000.0, "ethereum": 5000.0},
    )
    print()

    # 场景 5
    earn_discovery()
    composer_deposit_flow()
    intent_request()
