# 重复查询与信号字段（阶段三方法沉淀）

> 状态：`研究`（真实只读 API 报价，未签名、未授权、未广播）
> 来源：[LI.FI 文档](https://docs.li.fi/introduction/introduction)、LI.FI 公开 API `https://li.quest/v1/`
> 访问日期：2026-08-15
> 配套脚本：[`experiments/lifi_price_spread_watch.py`](../experiments/lifi_price_spread_watch.py)
> 对应日记：[`days/day-11.md`](../days/day-11.md)

## 一句话概括

把「手动查一次价差」升级为「带阈值的、可定时跑的、机器可读的查询」。任何机会字段都能套用同一个「输入 + 阈值 + 输出」模板，从一次性观察变成可持续监测的信号。

## 机会字段的三要素

| 要素 | 内容 | 跨链价差实例 |
| --- | --- | --- |
| **输入** | 链 id、token 地址、阈值、采样时间戳 | Base(8453) + Arbitrum(42161) 的 ETH、阈值 0.5% |
| **阈值** | 触发条件，须 ≥ 成本底价 | 价差 % ≥ 桥费 + Gas + 滑点 |
| **输出** | 机器可读，便于长期漂移分析 | JSON：时间戳 / 两链 priceUSD / 价差% / 是否触发 / 校验状态 |

## 脚本用法

```bash
python3 experiments/lifi_price_spread_watch.py \
  --chain-a 8453 --chain-b 42161 \
  --token-a 0x0000000000000000000000000000000000000000 \
  --token-b 0x0000000000000000000000000000000000000000 \
  --threshold 0.5 \
  --json-output experiments/raw/spread-$(date +%s).json
```

**退出码约定**（方便接 cron / Agent 判断）：

| exit code | 含义 |
| ---: | --- |
| `0` | 正常，未触发 |
| `1` | 触发阈值（有告警信号） |
| `3` | 符号不匹配，拒绝计算（需人工检查 token 地址） |

## 关键设计决策与坑

1. **`priceUSD` 是估值，不是可成交价** —— LI.FI 的 `priceUSD` 来自 CoinGecko（40+ 链 200 万+ 资产）。触发只是"初步筛查信号"，执行前必须用 `/v1/quote` 或 `advanced/routes` 验真实池子/订单簿价差。因此阈值要保守。
2. **同资产校验** —— 用 `symbol mismatch` 直接拒绝比较，防止把 USDC 和 USDC.e（或 Wrapped 变体）当成同一资产算出假价差。
3. **阈值经济学** —— 价差若低于桥费 + Gas + 滑点的成本底价，即便触发也无执行价值；阈值应把这些成本设进去。
4. **采样时间戳不可省** —— 没有时间戳的价差无法做漂移分析，也无法区分市场变化与报价时效。

## 实测记录

- ETH Base vs Arbitrum：`$1881.23` vs `$1881.46`，spread `0.012%`，远低于阈值，未触发 —— 同资产 paper spread 常态极小。
- USDC（原生 `0xaf88...`）vs USDC.e（`0xFF97...`）：触发 `symbol mismatch` 告警，拒绝计算。

## 下一步（接 day-12）

- 用 cron 定时跑该脚本，`exit 1` 时输出告警。
- 对固定输入重复采样，观察价差、价格与触发频率的漂移。
- 触发后接 `/v1/quote` 二次验证，形成「筛查 → 验证 → 记录」的最小工作流。

## 安全边界

仅只读报价研究，未签名、未授权、未广播；不使用真实账户或凭据。真实执行前须独立核验合约地址、审计历史、暂停/升级权限与可承受损失。
