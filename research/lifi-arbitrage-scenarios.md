# LI.FI 套利场景梳理

> 状态：`研究`（真实只读 API 报价，未签名、未授权、未广播）
> 来源：[LI.FI 文档](https://docs.li.fi/introduction/introduction)、LI.FI 公开 API `https://li.quest/v1/`
> 访问日期：2026-08-15
> 配套脚本：[`experiments/lifi_arb_scenarios.py`](../experiments/lifi_arb_scenarios.py)

## 一句话概括

LI.FI 是路由与执行层，能聚合跨链桥、同链 DEX、Solver 与收益协议。它对套利系统的价值不在"自动发现价差"，而在**报价、比较、执行和调仓**这四个环节——前提是使用者先把 Token 身份、成本结构和执行耗时想清楚。

## 已核验的公开 API 事实

| 端点 | 用途 | 返回要点 |
| --- | --- | --- |
| `GET /v1/token?chain=&token=` | 单个 token 元数据 | `symbol` / `name` / `decimals` / `priceUSD` / `verificationStatus` |
| `GET /v1/tokens?chains=` | 批量 token 元数据 | 同上，按 `chainId` 分组 |
| `GET /v1/quote?fromChain=&toChain=&fromToken=&toToken=&fromAmount=&fromAddress=` | 单条报价/route | `estimate.toAmount` / `toAmountMin` / `feeCosts` / `gasCosts` / `executionDuration`；`transactionRequest` |
| `POST /v1/advanced/routes` | 多候选 route 比较（生产用） | 需 integrator key，见 [EXP-2026-08-12-01](../experiments/EXP-2026-08-12-01.md) |

实测注意：`GET /v1/quote` 的 `fromAddress` 不能传 0 地址，否则返回 `code 1011`。

## 五个套利场景

### 1. 跨链套利：把跨链耗时算进去

- **例子**：同一时刻 ETH 在 Base 约 $1879.01、Arbitrum 约 $1879.54，纸面价差 0.028%。但跨链桥从发起到到账动辄 1~10 分钟，价差窗口往往只有几秒，且普通跨链流程未必原子。
- **结论**：Quote 看起来盈利 ≠ 资产到账时机会还在。更可行的做法是**多条链预先备资金，两端各自在本链吃价差，之后再用 LI.FI 做库存再平衡**——把"抓机会"和"跨链调仓"拆开。
- **代码**：`check_crosschain_spread()` 看纸面价差；`quote_crosschain()` 拆到账金额、耗时、桥费。

### 2. Token Price 与 Token Service：先辨清身份

- **例子**：同为 "USDC"，Arbitrum 原生 USDC `0xaf88...` 报 `priceUSD ≈ 1.000169`，桥接版 USDC.e `0xFF97...` 报 `≈ 0.999586`。地址/decimals/版本认错，后面所有价差比较全部失真。
- **结论**：任何价差比较之前，先用 `/v1/token` 锁定 `decimals` + `verificationStatus`。`priceUSD` 来自 CoinGecko（40+ 链 200 万+ 资产），可用于成本估值，但**交易机会仍以实际 Pool/Order Book 可成交价为准**。
- **代码**：`resolve_token()`。

### 3. Route 比较与同链 Swap：输出最多 ≠ 最优

- **例子**：同链 ETH→USDC，`toAmount` 报 1873.01 USDC，但 `toAmountMin` 只有 1863.65（滑点吃掉约 10 USDC）。多个候选 route 在 Gas、显式 Fee、模拟状态、动作数上差异很大。
- **结论**：比较用 `toAmountMin`（已含滑点），不能只看乐观的 `toAmount`；再叠加 Gas、Fee、`executionDuration`、动作数和故障恢复复杂度。`executionDuration` 在同链报价里可能返回 0，不能当真实执行时间。
- **代码**：`compare_samechain_routes()`；更完整的 7 候选对比见 [EXP-2026-08-12-01](../experiments/EXP-2026-08-12-01.md)。

### 4. 多链库存再平衡：调仓不抢时间

- **例子**：套利持续一段时间后，Arbitrum 侧 USDC 越堆越多、Base 侧越来越少（库存被推向一边）。实测从 Arbitrum 调 4000 USDC 回 Base，到账保底 3990、耗时约 7s。
- **结论**：再平衡不要求极低延迟，可以选桥费更低的慢 route，是普通跨链工具最合适的场景。
- **代码**：`rebalance_inventory()`。

### 5. Intents / Composer / Earn：套利之后的资金管理

- **Intents**：让 Solver 围绕一个目标结果（如"在 Base 拿到最多 USDC"）竞争执行。
- **Composer**：把「跨链 + deposit/stake/协议调用」打包成一次签名的原子交易。
- **Earn**：发现收益机会，把套利结束后的闲置稳定币调进收益仓位。
- **结论**：三者不等于套利策略本身，但扩展了资金管理的后续动作。需要 partner/integrator key，公开接口够不到。
- **代码**：`earn_discovery()` / `composer_deposit_flow()` / `intent_request()`（示意）。

## 关键坑位汇总

1. **跨链非原子**：Quote 盈利是静态快照，跨链到账耗时可能让价差消失。
2. **Token 版本混淆**：USDC vs USDC.e、Wrapped 变体，先 `/v1/token` 校验。
3. **`toAmount` vs `toAmountMin`**：后者已含滑点，才是比较基准。
4. **Fee 重复扣减**：Fee 常已包含在输入/输出数量流中，需判断 `included` 和步骤结构。
5. **`executionDuration=0`**：同链报价可能返回 0，无区分力，不代表零秒完成。
6. **`priceUSD` 是估值**：来自 CoinGecko，不代表可成交价。

## 安全边界

本笔记与配套脚本仅做只读报价研究与演示，未签名、未授权、未广播任何交易；不使用真实账户地址或凭据。真实执行前须独立核验合约地址、审计历史、暂停/升级权限与可承受损失。

## 未决问题

- 对固定输入定时重复采样，区分市场状态变化与报价时效造成的 route 漂移。
- 为工具风险补充协议审计、暂停权限与真实失败率数据。
- 比较同链单 Swap 与跨链多步 Route 的失败恢复与资金占用成本。
