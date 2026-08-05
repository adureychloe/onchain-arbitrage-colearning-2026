# 链上套利共学仓库框架实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立一个公开、Markdown 优先的 GitHub 学习仓库，支持 21 天每日记录、五阶段研究索引、实验与复盘，并带有基础质量检查。

**Architecture:** 根目录 README 作为导航和进度面板；`days/` 保存 21 篇固定编号的每日记录；`phases/`、`research/`、`experiments/`、`reviews/` 分别承担聚合视图、资料、实验和复盘。所有内容通过相对链接关联，模板集中在 `templates/`，公开边界和自动检查放在 `.gitignore` 与 `.github/`。

**Tech Stack:** Git、GitHub、Markdown、GitHub Actions（Markdown 链接检查与敏感信息模式扫描）。不引入运行时依赖或数据库。

---

### Task 1: 建立安全边界和项目入口

**Files:**
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: 写入忽略规则**

在 `.gitignore` 中加入 `.env`、密钥和钱包导出扩展名、系统文件、编辑器目录、运行日志及实验原始数据目录，确保公开仓库不会误收集凭据或本地缓存。

- [ ] **Step 2: 写入 README 导航**

README 必须包含课程链接、共学日期、项目目标、五阶段表格、21 天进度清单、目录导航、记录状态定义（研究/模拟/纸面交易/真实执行）和“非投资建议、不提交私钥/API 密钥”的公开声明。

- [ ] **Step 3: 检查入口链接**

运行 `rg -n '\[|\]\(' README.md`，确认 README 内的阶段、目录和课程外链均有对应目标；运行 `Test-Path` 检查列出的根目录是否将在后续任务创建。

- [ ] **Step 4: 提交入口文件**

```powershell
git add -- .gitignore README.md
git commit -m "add public learning repository entrypoint"
```

### Task 2: 创建五阶段索引和资料入口

**Files:**
- Create: `phases/01-arbitrage-map.md`
- Create: `phases/02-li-fi-routing.md`
- Create: `phases/03-hermes-workflow.md`
- Create: `phases/04-strategy-model.md`
- Create: `phases/05-capture-and-review.md`
- Create: `research/README.md`
- Create: `experiments/README.md`

- [ ] **Step 1: 为每个阶段写研究问题**

每个阶段页包含“阶段目标、关键问题、对应天数、每日记录链接表、阶段证据、当前结论、未决问题、下一步”，并分别覆盖套利机会结构、LI.FI 路由成本、Hermes 可重复工作流、净收益成本模型、信号捕获与复盘。

- [ ] **Step 2: 写资料与实验入口**

`research/README.md` 提供 LI.FI、Hermes、AMM/订单簿、Gas/滑点/桥费、数据源和术语的链接占位区；`experiments/README.md` 规定实验命名、输入/输出、复现步骤、脱敏和状态标签。

- [ ] **Step 3: 建立阶段到日记的固定链接**

五个阶段的每日范围固定为：阶段一 `day-01` 至 `day-04`，阶段二 `day-05` 至 `day-08`，阶段三 `day-09` 至 `day-12`，阶段四 `day-13` 至 `day-17`，阶段五 `day-18` 至 `day-21`。

- [ ] **Step 4: 提交阶段和入口页**

```powershell
git add -- phases research experiments
git commit -m "add phase and research indexes"
```

### Task 3: 编写可复用记录模板

**Files:**
- Create: `templates/daily-note.md`
- Create: `templates/experiment.md`
- Create: `templates/weekly-review.md`

- [ ] **Step 1: 写每日模板**

模板字段固定为日期、阶段、今日目标、完成内容、证据、观察与假设、反例、成本拆解（Gas/协议费/桥费/滑点/延迟/资金占用）、状态、结果、失败原因、可信度、明日行动和安全检查。

- [ ] **Step 2: 写实验模板**

模板字段固定为实验编号、问题、假设、输入、环境、步骤、输出、限制、结论、复现命令/查询、对应日记链接和状态。

- [ ] **Step 3: 写周复盘模板**

模板字段固定为覆盖日期、完成天数、关键证据、假设变化、失败模式、时间投入、风险边界、下一周行动和需要外部反馈的问题。

- [ ] **Step 4: 提交模板**

```powershell
git add -- templates
git commit -m "add daily experiment and review templates"
```

### Task 4: 生成 21 篇每日记录骨架和复盘文件

**Files:**
- Create: `days/day-01.md` through `days/day-21.md`
- Create: `reviews/week-01.md`
- Create: `reviews/week-02.md`
- Create: `reviews/week-03.md`
- Create: `reviews/final.md`

- [ ] **Step 1: 建立每日文件的固定元信息**

每篇文件写入编号、对应日期（day-01 为 2026-08-05，逐日递增至 day-21 为 2026-08-25；最终总结覆盖至 2026-08-26）、阶段和当天主题提示，并链接到 `templates/daily-note.md`。

- [ ] **Step 2: 写入阶段相关的起始问题**

根据五个阶段为每天写一个具体起始问题，例如比较价差与净收益、观察 LI.FI 路由变化、把一次查询变成可重复信号、建立成本模型、复盘信号真实性；正文保留空白供学习时填写。

- [ ] **Step 3: 建立周复盘链接**

`week-01` 覆盖 day-01 至 day-07，`week-02` 覆盖 day-08 至 day-14，`week-03` 覆盖 day-15 至 day-21；`final` 链接全部阶段页和三篇周复盘。

- [ ] **Step 4: 验证数量和文件名**

运行 `(Get-ChildItem days -Filter 'day-*.md').Count`，预期输出 `21`；运行 `Get-ChildItem days | Select-Object -ExpandProperty Name`，确认只有 `day-01.md` 至 `day-21.md`。

- [ ] **Step 5: 提交每日和复盘骨架**

```powershell
git add -- days reviews
git commit -m "add 21-day journal and review skeleton"
```

### Task 5: 加入公开协作入口和自动检查

**Files:**
- Create: `.github/ISSUE_TEMPLATE/learning-blocker.md`
- Create: `.github/ISSUE_TEMPLATE/experiment-proposal.md`
- Create: `.github/ISSUE_TEMPLATE/failure-review.md`
- Create: `.github/workflows/markdown-check.yml`

- [ ] **Step 1: 写三个 Issue 模板**

分别要求提交者填写上下文、已尝试内容、证据链接、期望反馈；实验提案还要填写假设、输入、预期输出和风险；失败复盘还要填写失败时间线、根因候选和下一次改进。

- [ ] **Step 2: 配置 Markdown 检查工作流**

工作流在 `push` 和 `pull_request` 上运行，使用固定版本的 `gaurav-nelson/github-action-markdown-link-check` 检查 Markdown 链接，并用 `rg` 检查常见凭据模式（`PRIVATE_KEY`、`MNEMONIC`、`API_KEY`、`BEGIN .* PRIVATE KEY`）。命中模式时工作流失败。

- [ ] **Step 3: 本地执行同等检查**

运行 `rg -n -i 'PRIVATE_KEY|MNEMONIC|API_KEY|BEGIN .* PRIVATE KEY' --glob '*.md' .`，预期无匹配；运行 `rg --files -g '*.md' | Measure-Object` 确认 Markdown 文件均被纳入检查范围。

- [ ] **Step 4: 提交协作和检查配置**

```powershell
git add -- .github
git commit -m "add issue templates and markdown checks"
```

### Task 6: 全量验证、创建公开 GitHub 仓库并推送

**Files:**
- Modify: `README.md`（将仓库链接替换为实际公开仓库地址）

- [ ] **Step 1: 检查工作区和提交历史**

运行 `git status --short --branch` 和 `git log --oneline --decorate -6`，确认只有本计划范围内的提交，工作区干净。

- [ ] **Step 2: 检查 GitHub CLI 环境**

运行 `gh --version` 和 `gh auth status`。若 CLI 不存在或未认证，停止发布步骤并向用户说明需要先安装/登录。

- [ ] **Step 3: 创建公开远程仓库**

确认 GitHub 账号下不存在同名仓库后，运行 `gh repo create onchain-arbitrage-colearning-2026 --public --source . --remote origin --push --description "21-day public learning log for on-chain arbitrage"`。

- [ ] **Step 4: 写回仓库地址并推送**

从 `git remote get-url origin` 获取仓库地址，将 README 顶部的仓库链接改为该地址，提交 `docs: link public repository`，再运行 `git push`。

- [ ] **Step 5: 验证公开仓库内容**

运行 `gh repo view --json nameWithOwner,isPrivate,defaultBranchRef,url`，预期 `isPrivate` 为 `false`；运行 `gh repo view --web` 或打开返回的 URL，确认 README、21 篇日记和 `.github` 配置均可见。

- [ ] **Step 6: 最终检查**

运行 `git status --short --branch`，预期无未提交修改；再次运行敏感信息扫描，预期无匹配；记录仓库 URL、默认分支、初始提交和后续每日记录入口。
