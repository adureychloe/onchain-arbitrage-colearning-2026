# Day-09｜2026-08-13｜Hermes 任务拆解

> 阶段：阶段三：用 Hermes 构建研究与信号工作流<br>
> 今日问题：如何把一个开放式研究问题拆成可执行的 Hermes 任务？

使用模板：[`daily-note.md`](../templates/daily-note.md)

## 今日目标

- 阅读 Hermes 文档，写出一个包含输入、工具和输出的任务拆解。

## 学习记录

- 完成内容：
  - 把开放式问题「跨链价差套利是否可行」拆成 4 个可执行的 Hermes 任务，每个任务写明**输入、工具、输出、人工复核点**。
- 证据链接：
  - 拆解结果见下方任务表；对应实现脚本见 [day-11 重复查询](../experiments/lifi_price_spread_watch.py)。
- 初始假设：开放式研究问题必须先拆成「输入 → 工具 → 输出」的稳定任务，才能交给 Agent 稳定、可复查地执行。
- 实际观察：同一个「跨链价差套利」问题，至少需要 4 个不同工具（token 元数据、价差脚本、quote 报价、记录写入）才能从"想法"落到"可复查证据"。
- 关键结论：拆解的关键不是"分几步"，而是**每一步的输出要能被下一步消费、且能被人工复核**——否则 Agent 会产出无法验证的结论。
- 明日行动：day-10 设计机会证据表，把 T4「记录」这一步的字段固定下来。

## 任务拆解表

开放式问题：**跨链价差套利是否可行？**

| 任务 | 输入 | 工具 | 输出 | 人工复核点 |
| --- | --- | --- | --- | --- |
| T1 辨资产 | `chainId` + token 地址 | `curl /v1/token` | `symbol` / `decimals` / `priceUSD` / `verificationStatus` | decimals 是 6 还是 18？USDC 还是 USDC.e？ |
| T2 查价差 | 两链 + token 地址 + 阈值 | `lifi_price_spread_watch.py` | `spread_pct` / `triggered` / exit code | `priceUSD` 是 CoinGecko 估值，非可成交价 |
| T3 验可成交 | `fromChain/toChain/fromToken/toToken/fromAmount/fromAddress` | `curl /v1/quote` | `toAmountMin` / `feeCosts` / `gasCosts` / `executionDuration` | 用 `toAmountMin` 而非 `toAmount`；Fee 是否已含在数量流中 |
| T4 记录 | T1–T3 输出 | 写 JSON / Markdown | 结构化机会记录 | 时间戳、状态标注（研究/模拟/纸面/真实）不可省 |

**关键设计**：T4 的记录字段由 day-10 统一固定，T2/T3 的脚本都输出机器可读 JSON，保证「筛查 → 验证 → 记录」闭环可被下一任务直接消费。

## 复盘备注

- 哪个判断被证据改变：一开始以为"拆解 = 列步骤"，实际发现"拆解 = 保证每步输出可复核、可被下一步消费"。
- 还缺哪一条证据：记录字段的固定 schema（day-10）。
