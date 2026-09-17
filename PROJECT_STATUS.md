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
- 快照核实日期：2026-09-18。
- 当前内容工作分支：`c-mode-v2-2013-2018-production`。
- 核实到的内容提交：[`6f37091d156392a89b774a4f5b52e6a3c3464dea`](https://github.com/dannhitruong852-jpg/taptap/commit/6f37091d156392a89b774a4f5b52e6a3c3464dea)，提交信息 `stage: persist 2017 V2 review evidence`。
- 当前批次：2013—2018，每年 cloze、text1—text4、partb、translation 共七篇。
- 最近用户要求：跨窗口固定一句话恢复；恢复后直接继续既定生产；每个可恢复小任务及时保存并更新本入口。

| 年份 | 已核实的仓库状态 | 尚不能声称完成的部分 |
|---|---|---|
| 2013—2015 | 每年五个 curated 分片、七个独立 candidate 文件；均有 reviewed bilingual-highlights 源文件 | 当前分支尚未核实到这些年份的编译后网站内容和音频；文件存在不等于本批正式质量门禁全通过 |
| 2016 | 五个分片可完整解压、解析；七篇源稿共 122 个句子单元；七个独立 candidate 文件均已保存为 `reviewed_candidate` | 尚未核实到 2016 编译后网站内容、reviewed bilingual-highlights 和音频；未完成本批正式校验/冻结 |
| 2017 | 五个分片完整；七篇编译内容共 131 个句子单元；有 direction、voice_profiles、extraction；七个独立 candidate 文件已保存 | 尚无 2017 reviewed bilingual-highlights、音频、本批全量正式质量校验、冻结及发布完成证据 |
| 2018 | 当前工作分支未见对应 curated、candidate、编译内容、双语标注或音频 | 待按原始 PDF 和既定规则生产该年七篇 |

批次清单仍为 `state=draft`、`freeze=null`、`artifacts={}`。清单的 `source_ref=b9c5fde97cd854383164031455f43857154b3bda` 已落后于当前完整源稿/候选稿状态，完整源稿入库后必须更新，不能按旧 ref 冻结。

旧截图中的“2017 仅 part00/part01、恢复 16,314 字符、gzip eof=false、断在 Parents, he says…”已经失效；2017 现为完整七篇，禁止从旧断点重做。

## 3. 最新证据与运行

- [2017 candidate 检查点提交](https://github.com/dannhitruong852-jpg/taptap/commit/6f37091d156392a89b774a4f5b52e6a3c3464dea)：一次提交补齐 2017 七个独立 candidate 文件；远端目录已回读确认 7/7 存在。
- [该提交触发的 Stage Audit](https://github.com/dannhitruong852-jpg/taptap/actions/runs/35250800971)：输入提交 `6f37091d156392a89b774a4f5b52e6a3c3464dea`，已完成且 `success`。这是阶段审计，不等同于正式 V2 全批次校验/冻结。
- [2017 重建提交](https://github.com/dannhitruong852-jpg/taptap/commit/5297bcc6bf47c401624fd458cf99ca2ddc1f7ec5)：五个源分片、七篇编译内容和相关报告。
- [成功的 2017 重建运行](https://github.com/dannhitruong852-jpg/taptap/actions/runs/35236793342)：基础重建成功；其 artifact 后续被复用核对七篇、131 个句子单元。
- 2017 原始 PDF SHA-256：`88dc4ff8e9faa7bfca02a6361968200aec269c705a39bb66b7791fea95403aa4`。
- 当前另有 [C Mode Rebuild 2017 run 35250800974](https://github.com/dannhitruong852-jpg/taptap/actions/runs/35250800974) 由上述内容提交的 push 自动触发；写本快照时仍在运行。该工作流只重建/编译 2017 canonical source 并在有差异时提交，不会写 `reports/content-freeze/2017`。接手时必须先核对该 run 最终结果及工作分支 HEAD，避免与其并发。
- [批次清单](https://github.com/dannhitruong852-jpg/taptap/blob/c-mode-v2-2013-2018-production/batch-manifests/2013-2018.json)。
- [源稿目录](https://github.com/dannhitruong852-jpg/taptap/tree/c-mode-v2-2013-2018-production/content-pipeline/curated)。
- [候选稿目录](https://github.com/dannhitruong852-jpg/taptap/tree/c-mode-v2-2013-2018-production/reports/content-freeze)。
- [2017 提取报告](https://github.com/dannhitruong852-jpg/taptap/blob/c-mode-v2-2013-2018-production/reports/extraction/2017.json)。
- 用户提供的 2017、2018 及其他年度 PDF 曾在会话附件中可用。临时绝对路径不能作为跨窗口保证；读取源文件前要核验当轮可用文件及身份，不凭旧路径断言存在。

## 4. 已确定的规则

遵守用户当轮指令及仓库现行规范，不重新设计既定产品：

- 原始 PDF 是正文依据，沿用既定范围、信达雅翻译要求、15 演员总纲和 C 模式规则；具体细节读取下面的现行规范。
- [PRODUCTION_RULES.md](https://github.com/dannhitruong852-jpg/taptap/blob/c-mode-v2-2013-2018-production/PRODUCTION_RULES.md)。
- [C_MODE_PRODUCTION_V2.md](https://github.com/dannhitruong852-jpg/taptap/blob/c-mode-v2-2013-2018-production/docs/production/C_MODE_PRODUCTION_V2.md)。
- [V2 设计](https://github.com/dannhitruong852-jpg/taptap/blob/c-mode-v2-2013-2018-production/docs/superpowers/specs/2026-09-17-c-mode-production-pipeline-v2-design.md)。
- 状态顺序：draft → validated → frozen → rendering → merged → release_candidate → published。冻结前不进行大规模语音生成。
- 先保留和复用已完成部分，只补失败或缺失单元。发布保留此前全部年份和文章。
- [9 月 12 日旧交接](https://github.com/dannhitruong852-jpg/taptap/blob/c-mode-v2-2013-2018-production/docs/handoff/2026-09-12-kaoyan-project-handoff.md)用于查历史需求；其 CURRENT STATE 已过时，不作最新进度依据。

## 5. 下一步与检查点

继续生产时按下面顺序执行：
1. 先核对 run `35250800974` 最终结果和当前工作分支 HEAD；若它产生新提交，以新 HEAD 为基准，不覆盖。
2. 补齐 2016、2017 reviewed bilingual-highlights，并补齐/核实 2013—2016 编译内容及对应 QA；2017 candidate 已完成，不重复生成。
3. 按原始 2018 PDF 和既定规则完成 2018 七篇源稿、candidate、双语标注、编译内容和质量证据；每篇或可恢复小批次及时提交。
4. 所有源稿/审核证据齐备后更新 batch `source_ref`，运行正式 V2 全批次校验；只有通过后才进入 freeze，再生成音频、合并验收及发布。
5. 每个检查点更新本文件，记录确切内容提交、已执行检查、失败/待办和下一项可执行动作。

## 6. 存档维护协议（每个执行窗口都须遵守）

- 这是唯一的跨窗口最新状态入口；不要另建一份同名但不同步的权威状态。
- 完成一个可独立恢复的小任务、遇到阻塞、改变工作分支或准备结束本轮时，保存实际成果，并更新本文件。长任务中途也要建检查点。
- 成果提交到工作分支；确认远端保存后，将内容提交 SHA 和状态更新提交到 main。本入口与内容分支是两次提交，不声称它们具有原子一致性。若在两次提交之间中断，下次按 HEAD 差异恢复。
- 如果修改本文件本身，记录“核实到的内容提交”；不要要求本文件包含自身提交 SHA，以免循环修改。
- 使用当前 main HEAD 为父提交，非强制推送；若发生并发冲突，重新读取、整合其他窗口的新状态，不覆盖。多个窗口先划分任务；文档中的分工记录并不是自动互斥锁。
- 只把有证据的阶段标记完成。写清“源稿已保存 / 基础检查通过 / 正式校验通过 / 已冻结 / 音频完成 / 已发布”的区别。
- 记录运行链接和输入提交，重新检查异步任务是否结束；不重复启动已经运行或完成的相同任务。
- 更新已有状态，保持简短，历史由 Git 保存。新决策写入相应长期规范，并在这里链接。
- 推送前检查目标分支工作流触发条件，避免只为存档触发生产。main 文档专用提交可使用 `[skip ci]` 避免现有 push 型 APK 构建；不要用它绕过真实代码或内容的必要验证。
- 推送后回读 main 上的本文件及目标工作分支，确认已保存，才向用户报告存档完成。
- 本机制目前是仓库文档与执行协议；未安装定时保存、自动进度生成、自动互斥或强制 CI 状态门禁。必须由执行任务的会话落实更新，不能承诺捕获突然中断前尚未保存的工作。
