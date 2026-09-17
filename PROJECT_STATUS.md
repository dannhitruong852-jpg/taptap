# 英语真题项目：固定接手入口

> 新窗口每次只需发送同一句话：
> 请读取 GitHub 仓库 dannhitruong852-jpg/taptap 的 main 分支根目录 PROJECT_STATUS.md，按其中的接手流程恢复最新项目状态。

本文件永久位于 `main:/PROJECT_STATUS.md`。工作分支改变时更新本文件，用户无需改变口令。这里保存已落库的工作状态、决策和恢复线索，不代表能恢复未保存的聊天或临时文件。

## 1. 接手流程（先读这一节）

1. 读取本文件和 [main 的 AGENTS.md](https://github.com/dannhitruong852-jpg/taptap/blob/main/AGENTS.md)。
2. 根据下方记录找到当前工作分支，读取其真实远端 HEAD。禁止把 main 的旧安卓应用当成英语真题源码。
3. 若 HEAD 与下方“核实到的内容提交”一致，可使用此快照；若不同，检查之后的提交、相关文件和 Actions，先校正状态。即使 HEAD 一致，也检查是否有后来启动或完成的相关任务。
4. 按需读取链接的生产规则、当前批次清单和与下一步相关的文件。不需要通读所有旧聊天、历史交接和全部源码。
5. 恢复后简短报告当前断点、待办和差异。用户只说“恢复状态”时停在核对；用户明确要求“继续做”时，按既定规则继续，不重新讨论已确定的需求。
6. GitHub 证据优先于本快照。无法验证的状态标记“待核实”，不要把缺少记录推断为成功。无访问权限时明确说明，不臆造恢复结果。

## 2. 当前工作快照

- 项目：考研英语真题 C 模式学习网站。
- 仓库：`dannhitruong852-jpg/taptap`。
- 快照核实日期：2026-09-17（本次依据下列确切提交核实）。
- 当前内容工作分支：`c-mode-v2-2013-2018-production`。
- 核实到的内容提交：[`5297bcc6bf47c401624fd458cf99ca2ddc1f7ec5`](https://github.com/dannhitruong852-jpg/taptap/commit/5297bcc6bf47c401624fd458cf99ca2ddc1f7ec5)。
- 该提交时间：2026-09-17 22:55:31（北京时间）。
- 当前批次：2013—2018，每年 cloze、text1—text4、partb、translation 共七篇。
- 最近用户要求：固定一句话即可跨窗口恢复最新项目状态；每个小任务及时保存成果和更新本入口。
- 本轮范围：建立接手与存档文档。未继续真题生产，未主动启动音频、发布或恢复任务。

| 年份 | 已核实的仓库状态 | 尚不能声称完成的部分 |
|---|---|---|
| 2013—2015 | 每年五个 curated 分片、七个独立 candidate 文件；2013—2015 有 bilingual-highlights 文件 | 当前分支没有这些年份的编译后网站内容和音频；文件存在不等于质量门禁全通过 |
| 2016 | 五个分片能完整解压、解析；含七篇源稿，合计 122 个句子单元，标记 reviewed_candidate | 无独立 candidate 文件、编译后网站内容和音频；待按正式规则补齐和验证 |
| 2017 | 五个分片完整；七篇已编译内容，共 131 个句子单元；有 direction、voice_profiles、extraction 报告；基础重建检查成功 | 无独立 candidate 文件和音频；尚无本批全量质量校验、冻结及发布完成证据 |
| 2018 | 当前工作分支未见对应 curated、candidate、编译内容或音频 | 待生产该年内容 |

批次清单仍为 `state=draft`、`freeze=null`、`artifacts={}`。清单的 `source_ref=b9c5fde97cd854383164031455f43857154b3bda` 是旧提交，继续前必须检查其与完整源稿快照的关系，不能误用旧输入。

旧截图中的“2017 仅 part00/part01、恢复 16,314 字符、gzip eof=false、断在 Parents, he says…”已被最新提交修复。2017 现在 gzip 完整，禁止从旧断点重做整年前半部分。

## 3. 本快照的证据入口

- [2017 重建提交](https://github.com/dannhitruong852-jpg/taptap/commit/5297bcc6bf47c401624fd458cf99ca2ddc1f7ec5)：五个源分片、七篇编译内容和相关报告。
- [成功的 2017 重建运行](https://github.com/dannhitruong852-jpg/taptap/actions/runs/35236793342)：输入提交 b2954dfe3c36600435fc7781a06495a79ae814f2，成功产出上面的内容提交。它是基础重建核验，不是完整 V2 发布验收。
- [批次清单](https://github.com/dannhitruong852-jpg/taptap/blob/c-mode-v2-2013-2018-production/batch-manifests/2013-2018.json)。
- [源稿目录](https://github.com/dannhitruong852-jpg/taptap/tree/c-mode-v2-2013-2018-production/content-pipeline/curated)。
- [候选稿目录](https://github.com/dannhitruong852-jpg/taptap/tree/c-mode-v2-2013-2018-production/reports/content-freeze)。
- [2017 提取报告](https://github.com/dannhitruong852-jpg/taptap/blob/c-mode-v2-2013-2018-production/reports/extraction/2017.json)。
- 2017 原始 PDF SHA-256：`88dc4ff8e9faa7bfca02a6361968200aec269c705a39bb66b7791fea95403aa4`，本轮与用户提供 PDF 核对一致。
- 用户提供的 2017、2018 及其他年度 PDF 曾在会话附件中可用。临时绝对路径不能作为跨窗口保证；新窗口应查当轮附件或持久化来源，读取源文件前验证身份，不能凭旧路径断言存在。

## 4. 已确定的规则

遵守用户当轮指令及仓库现行规范，不重新设计既定产品：

- 原始 PDF 是正文依据，沿用已确定的范围、信达雅翻译要求、15 演员总纲和 C 模式规则；具体细节读取下面的现行规范。
- [PRODUCTION_RULES.md](https://github.com/dannhitruong852-jpg/taptap/blob/c-mode-v2-2013-2018-production/PRODUCTION_RULES.md)。
- [C_MODE_PRODUCTION_V2.md](https://github.com/dannhitruong852-jpg/taptap/blob/c-mode-v2-2013-2018-production/docs/production/C_MODE_PRODUCTION_V2.md)。
- [V2 设计](https://github.com/dannhitruong852-jpg/taptap/blob/c-mode-v2-2013-2018-production/docs/superpowers/specs/2026-09-17-c-mode-production-pipeline-v2-design.md)。
- 状态顺序：draft → validated → frozen → rendering → merged → release_candidate → published。冻结前不进行大规模语音生成。
- 先保留和复用已完成部分，只补失败或缺失单元。发布保留此前全部年份和文章。
- [9 月 12 日旧交接](https://github.com/dannhitruong852-jpg/taptap/blob/c-mode-v2-2013-2018-production/docs/handoff/2026-09-12-kaoyan-project-handoff.md)用于查历史需求；其 CURRENT STATE 已过时，不作最新进度依据。

## 5. 下一步与检查点

收到继续生产的指令后：
1. 重新核对当前分支 HEAD、未完成或已完成的 Actions，避免重复运行；已有运行的结果优先复用。
2. 检查并补齐 2013—2017 候选稿、双语标注、编译内容和质量证据的缺口。2017 只通过基础检查，不跳过正式质量门禁。
3. 按原始 PDF 和既定规则完成 2018，每篇或可恢复的小批次及时提交。
4. 完整源稿入库后，核对并更新批次 source_ref，经正式 V2 流程完成校验和冻结；随后再生成音频、合并验收及发布。
5. 每个检查点更新本文件，记录确切内容提交、已执行的检查、失败或待办、下一项可执行动作。

本次未新增运行中的生产任务。接手时应现场检查 Actions，不把本句当成永久运行状态。

## 6. 存档维护协议（每个执行窗口都须遵守）

- 这是唯一的跨窗口最新状态入口；不要另建一份同名但不同步的权威状态。
- 完成一个可独立恢复的小任务、遇到阻塞、改变工作分支或准备结束本轮时，保存实际成果，并更新本文件。长任务中途也要建检查点。
- 成果提交到工作分支；确认远端保存后，将内容提交 SHA 和状态更新提交到 main。本入口与内容分支是两次提交，不声称它们具有原子一致性。若在两次提交之间中断，下次按 HEAD 差异恢复。
- 如果修改本文件本身，记录“核实到的内容提交”；不要要求本文件包含自身提交 SHA，以免循环修改。
- 使用当前 main HEAD 为父提交，非强制推送；若发生并发冲突，重新读取、整合其他窗口的新状态，不覆盖。多个窗口先划分任务；文档中的分工记录并不是自动互斥锁。
- 只把有证据的阶段标记完成。写清“源稿已保存 / 基础检查通过 / 正式校验通过 / 已冻结 / 音频完成 / 已发布”的区别。
- 记录运行链接和输入提交，重新检查异步任务是否结束；不重复启动已经运行或完成的相同任务。
- 更新已有状态，保持简短，历史由 Git 保存。新決策写入相应长期规范，并在这里链接。
- 推送前检查目标分支工作流触发条件，避免只为存档触发生产。main 文档专用提交可使用 `[skip ci]` 避免现有 push 型 APK 构建；不要用它绕过真实代码或内容的必要验证。
- 推送后回读 main 上的本文件及目标工作分支，确认已保存，才向用户报告存档完成。
- 本机制目前是仓库文档与执行协议；未安装定时保存、自动进度生成、自动互斥或强制 CI 状态门禁。必须由执行任务的会话落实更新，不能承诺捕获突然中断前尚未保存的工作。
