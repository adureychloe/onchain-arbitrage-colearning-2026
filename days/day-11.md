# Day-11｜2026-08-15｜重复查询与信号字段

> 阶段：阶段三：用 Hermes 构建研究与信号工作流<br>
> 今日问题：一次性观察怎样变成可重复查询、告警或 Agent 工作流？

使用模板：[`daily-note.md`](../templates/daily-note.md)

## 今日目标

- 选择一个机会字段，设计重复查询的输入、阈值和输出格式。

## 学习记录

- 完成内容：
  - 选定机会字段「跨链价差」（cross-chain price spread）：同一资产在两个链上的 CoinGecko `priceUSD` 之差。
  - 编写重复查询脚本 [`lifi_price_spread_watch.py`](../experiments/lifi_price_spread_watch.py)，固定输入、阈值和输出格式，可配合 cron 反复运行。
  - 用真实只读数据验证两种情形：同资产跨链比较、以及 USDC vs USDC.e 的符号不匹配告警。
- 证据链接：
  - [重复查询脚本](../experiments/lifi_price_spread_watch.py)
  - 脚本的 `--json-output` 输出即结构化机会记录，见下方「实际观察」。
- 初始假设：把「查一次价差」升级为「带阈值的重复查询」，能让价差机会从手动观察变成可告警的信号。
- 实际观察：
  - ETH 在 Base（`8453`）与 Arbitrum（`42161`）实测 `priceUSD` 差仅 `0.012%`，远低于 `0.3%` 阈值，未触发；说明同资产 paper spread 常态下极小。
  - USDC（原生 `0xaf88...`）与 USDC.e（`0xFF97...`）被脚本以 `symbol mismatch` 拒绝计算价差，避免把不同资产误当成同一资产比较。
- 关键结论：
  - 机会字段的「输入」应含：链 id、token 地址、阈值、采样时间戳；「输出」必须机器可读（JSON）才便于长期漂移分析。
  - 阈值必须保守：`priceUSD` 是 CoinGecko 估值而非可成交价，触发后仍需用 `/v1/quote` 验证真实可成交价差。
  - 若价差低于桥费 + Gas + 滑点的成本底价，即使触发也无可执行价值；阈值应把成本底价设进去。
- 明日行动：day-12 运行一次最小研究工作流，把该脚本接成定时/重复运行，并记录人工复核点。
