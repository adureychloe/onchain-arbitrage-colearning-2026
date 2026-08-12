#!/usr/bin/env python3
"""Compare LI.FI advanced routes without signing or broadcasting a transaction.

The script calls POST /v1/advanced/routes, keeps the full response locally when
--raw-output is supplied, and emits a compact JSON/Markdown comparison.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

API_URL = "https://li.quest/v1/advanced/routes"
DEFAULT_ADDRESS = "0x1111111111111111111111111111111111111111"


def decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def token_amount(raw: Any, decimals: int) -> Decimal:
    return decimal(raw) / (Decimal(10) ** decimals)


def walk_steps(route: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    def visit(step: dict[str, Any]) -> None:
        result.append(step)
        for child in step.get("includedSteps") or []:
            visit(child)

    for step in route.get("steps") or []:
        visit(step)
    return result


def fee_summary(steps: list[dict[str, Any]]) -> tuple[Decimal, list[str]]:
    total = Decimal("0")
    labels: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for step in steps:
        for fee in (step.get("estimate") or {}).get("feeCosts") or []:
            key = (str(fee.get("name", "fee")), str(fee.get("amount", "")), str(fee.get("amountUSD", "")))
            # Parent LI.FI steps often repeat fees already shown in included steps.
            if key in seen:
                continue
            seen.add(key)
            usd = decimal(fee.get("amountUSD"))
            total += usd
            labels.append(f"{key[0]} ${usd:.4f}")
    return total, labels


def route_risk(route: dict[str, Any], steps: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """Return a transparent research heuristic, not a LI.FI security rating."""
    reasons: list[str] = []
    points = 0
    simulation = route.get("routeSimulation", "unknown")
    if simulation == "success":
        reasons.append("route simulation succeeded")
    elif simulation in {"failed", "reverted"}:
        points += 4
        reasons.append(f"route simulation={simulation}")
    else:
        points += 1
        reasons.append(f"route simulation={simulation}")

    executable = [s for s in steps if s.get("type") not in {"protocol"}]
    if len(executable) > 1:
        points += min(3, len(executable) - 1)
        reasons.append(f"{len(executable)} executable actions")
    else:
        reasons.append("single executable action")

    if route.get("containsSwitchChain"):
        points += 2
        reasons.append("requires chain switch")

    tokens = [route.get("fromToken") or {}, route.get("toToken") or {}]
    unverified = [t.get("symbol", "?") for t in tokens if t.get("verificationStatus") not in {None, "verified"}]
    if unverified:
        points += 3
        reasons.append("unverified token: " + ", ".join(unverified))
    else:
        reasons.append("endpoint tokens verified")

    if points <= 1:
        level = "low"
    elif points <= 3:
        level = "medium"
    else:
        level = "high"
    return level, reasons


def summarize_route(route: dict[str, Any], index: int) -> dict[str, Any]:
    to_token = route.get("toToken") or {}
    decimals = int(to_token.get("decimals", 18))
    price = decimal(to_token.get("priceUSD"))
    minimum = token_amount(route.get("toAmountMin"), decimals)
    expected = token_amount(route.get("toAmount"), decimals)
    gas = decimal(route.get("gasCostUSD"))
    steps = walk_steps(route)
    fee_usd, fee_labels = fee_summary(steps)
    durations = [decimal((s.get("estimate") or {}).get("executionDuration")) for s in steps]
    duration = sum(durations, Decimal("0"))
    tools: list[str] = []
    for step in steps:
        tool = step.get("tool")
        if tool and tool not in {"feeCollection"} and tool not in tools:
            tools.append(str(tool))
    risk, risk_reasons = route_risk(route, steps)
    min_usd = minimum * price
    effective_min_usd = min_usd - gas
    executable_steps = sum(1 for s in steps if s.get("type") != "protocol")
    return {
        "rank": index,
        "route_id": route.get("id"),
        "tags": route.get("tags") or [],
        "tools": tools,
        "to_symbol": to_token.get("symbol"),
        "to_amount": str(expected),
        "to_amount_min": str(minimum),
        "to_amount_min_usd": str(min_usd.quantize(Decimal("0.0001"))),
        "gas_cost_usd": str(gas.quantize(Decimal("0.0001"))),
        "effective_min_after_gas_usd": str(effective_min_usd.quantize(Decimal("0.0001"))),
        "fee_cost_usd": str(fee_usd.quantize(Decimal("0.0001"))),
        "fee_details": fee_labels,
        "duration_seconds": float(duration),
        "top_level_steps": len(route.get("steps") or []),
        "executable_steps": executable_steps,
        "all_step_types": [str(s.get("type")) for s in steps],
        "simulation": route.get("routeSimulation", "unknown"),
        "risk": risk,
        "risk_reasons": risk_reasons,
    }


def recommend(routes: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not routes:
        return None
    safe = [r for r in routes if r["risk"] != "high"] or routes
    best_effective = max(decimal(r["effective_min_after_gas_usd"]) for r in safe)
    # Treat routes within 0.05% of the best minimum result as economically tied,
    # then prefer lower uncertainty, fewer actions, lower gas, and shorter duration.
    tolerance = max(Decimal("0.01"), abs(best_effective) * Decimal("0.0005"))
    near_best = [r for r in safe if best_effective - decimal(r["effective_min_after_gas_usd"]) <= tolerance]
    risk_order = {"low": 0, "medium": 1, "high": 2}
    return min(
        near_best,
        key=lambda r: (
            risk_order.get(r["risk"], 9),
            r["executable_steps"],
            decimal(r["gas_cost_usd"]),
            decimal(r["duration_seconds"]),
            -decimal(r["effective_min_after_gas_usd"]),
        ),
    )


def markdown_report(document: dict[str, Any]) -> str:
    req = document["request"]
    lines = [
        "# LI.FI Route 比较：同链 Swap",
        "",
        f"- 查询时间（UTC）：`{document['queried_at_utc']}`",
        f"- 路线：Chain `{req['fromChainId']}` 上 `{document['from_symbol']}` → `{document['to_symbol']}`",
        f"- 输入：`{document['from_amount_display']} {document['from_symbol']}`",
        f"- 滑点：`{req['options']['slippage'] * 100:.2f}%`",
        f"- 返回候选：`{len(document['routes'])}`",
        "- 状态：只读报价；未签名、未授权、未广播交易",
        "",
        "## 候选 Route",
        "",
        "| API序号 | 工具 | toAmountMin | 最低到账USD | Gas USD | Fee USD | Duration | 动作数 | 模拟 | 风险启发式 | 标签 |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for r in document["routes"]:
        lines.append(
            "| {rank} | {tools} | {minimum} {symbol} | ${min_usd} | ${gas} | ${fee} | {duration:.0f}s | {actions} | {simulation} | {risk} | {tags} |".format(
                rank=r["rank"], tools=" + ".join(r["tools"]) or "-", minimum=r["to_amount_min"],
                symbol=r["to_symbol"], min_usd=r["to_amount_min_usd"], gas=r["gas_cost_usd"],
                fee=r["fee_cost_usd"], duration=r["duration_seconds"], actions=r["executable_steps"],
                simulation=r["simulation"], risk=r["risk"], tags=", ".join(r["tags"]) or "-",
            )
        )
    rec = document.get("recommended")
    lines += ["", "## 选择结果", ""]
    if rec:
        lines += [
            f"推荐 Route：API 序号 **{rec['rank']}**，工具 **{' + '.join(rec['tools'])}**。",
            "",
            f"理由：先排除高风险候选；将净最低到账差距在 0.05% 内的路径视为近似同价，再比较模拟状态、动作数、Gas 和 Duration。该 Route 的 `toAmountMin` 为 `{rec['to_amount_min']} {rec['to_symbol']}`，Gas 约 `${rec['gas_cost_usd']}`，风险启发式为 `{rec['risk']}`。",
        ]
    lines += [
        "",
        "## 风险字段说明",
        "",
        "`risk` 不是 LI.FI 官方安全评级，而是本实验的透明启发式：根据 Route 模拟状态、可执行动作数、是否切链及端点代币验证状态分级。工具合约、审计历史、暂停状态和真实失败率仍需单独核验。",
        "",
        "Fee 可能已经从输入或输出中扣除，因此不能再机械地从 `toAmountMin` 重复扣减；本报告单列 Fee，并使用 `toAmountMin × 目标币价格 - Gas` 作为跨 Route 的保守比较值。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--from-chain", type=int, required=True)
    p.add_argument("--to-chain", type=int, required=True)
    p.add_argument("--from-token", required=True)
    p.add_argument("--to-token", required=True)
    p.add_argument("--from-amount", required=True, help="Integer amount including token decimals")
    p.add_argument("--from-address", default=DEFAULT_ADDRESS)
    p.add_argument("--to-address", default=DEFAULT_ADDRESS)
    p.add_argument("--slippage", type=float, default=0.005)
    p.add_argument("--order", choices=["CHEAPEST", "FASTEST"], default="CHEAPEST")
    p.add_argument("--max-price-impact", type=float, default=0.1)
    p.add_argument("--raw-output", type=Path)
    p.add_argument("--json-output", type=Path)
    p.add_argument("--markdown-output", type=Path)
    args = p.parse_args()

    payload = {
        "fromChainId": args.from_chain,
        "toChainId": args.to_chain,
        "fromTokenAddress": args.from_token,
        "toTokenAddress": args.to_token,
        "fromAmount": args.from_amount,
        "fromAddress": args.from_address,
        "toAddress": args.to_address,
        "options": {"slippage": args.slippage, "order": args.order, "maxPriceImpact": args.max_price_impact},
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json", "user-agent": "onchain-arbitrage-colearning/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(errors="replace"), file=sys.stderr)
        return 2
    data = json.loads(raw)
    if args.raw_output:
        args.raw_output.parent.mkdir(parents=True, exist_ok=True)
        args.raw_output.write_bytes(json.dumps(data, ensure_ascii=False, indent=2).encode())

    routes = [summarize_route(route, i) for i, route in enumerate(data.get("routes") or [], start=1)]
    first = (data.get("routes") or [{}])[0]
    from_token = first.get("fromToken") or {}
    to_token = first.get("toToken") or {}
    document = {
        "queried_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": API_URL,
        "request": payload,
        "from_symbol": from_token.get("symbol", "FROM"),
        "to_symbol": to_token.get("symbol", "TO"),
        "from_amount_display": str(token_amount(args.from_amount, int(from_token.get("decimals", 0)))),
        "routes": routes,
        "recommended": recommend(routes),
        "unavailable_route_failures": sum(len(x.get("subpaths", {}).get(k, [])) for x in (data.get("unavailableRoutes", {}).get("failed") or []) for k in x.get("subpaths", {})),
        "risk_method": "research heuristic; not an official LI.FI security rating",
    }
    compact = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    report = markdown_report(document)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(compact)
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(report)
    if not args.json_output and not args.markdown_output:
        print(report)
    else:
        print(f"routes={len(routes)} recommended={document['recommended']['rank'] if document['recommended'] else 'none'}")
    return 0 if routes else 3


if __name__ == "__main__":
    raise SystemExit(main())
