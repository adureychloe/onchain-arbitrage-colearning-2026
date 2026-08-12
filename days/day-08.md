# Day-08｜2026-08-12｜复现路由观察

> 阶段：阶段二：使用 LI.FI 发现路径与机会<br>
> 今日问题：能否把一条路由观察复现，并解释报价差异的来源？

使用模板：[`daily-note.md`](../templates/daily-note.md)

## 今日目标

- 完成一个可复现的 LI.FI 路由实验并记录限制。

## 学习记录

- 完成内容：
  - 调用 LI.FI `POST /v1/advanced/routes`，对 Arbitrum 上 `1,000 USDC → WETH` 做真实只读同链 Swap 路由比较。
  - API 返回 7 个候选工具；逐条比较 `toAmountMin`、Gas、显式 Fee、Duration、模拟状态、动作数和风险启发式。
  - 实现可复现脚本，自动保存结构化摘要和 Markdown 报告，全程未签名、未授权、未广播。
- 证据链接：
  - [完整实验记录](../experiments/EXP-2026-08-12-01.md)
  - [Route 对比报告](../experiments/EXP-2026-08-12-01-report.md)
  - [结构化摘要](../experiments/EXP-2026-08-12-01-summary.json)
  - [复现脚本](../experiments/lifi_route_compare.py)
- 初始假设：最高 `toAmount` 不一定是最适合执行的 Route，应优先观察 `toAmountMin`，再考虑 Gas、Fee、模拟状态、步骤复杂度和恢复难度。
- 实际观察：本次最高输出候选 Nordstern 同时也是综合最优，未出现“最高输出却落选”的最终反例；但 Bitget 展示了“输出接近、Gas 显著更高且未成功模拟”，SushiSwap 展示了“Gas 最低、额外协议费和最低到账更差”。
- 关键结论：Fee 可能已包含在 Route 数量流中，不能从 `toAmountMin` 再重复扣除；本次 `executionDuration=0` 没有区分力，也不等于真实零秒成交。
- 明日行动：固定输入按时间重复采样，观察 Route 排名、Gas 和模拟状态漂移，并加入跨链多步 Route 做复杂度对照。
