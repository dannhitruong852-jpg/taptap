# 英语真题项目：固定接手入口

> 请读取 GitHub 仓库 dannhitruong852-jpg/taptap 的 main 分支根目录 PROJECT_STATUS.md，按其中的接手流程恢复最新项目状态。

## 接手流程
1. 读取本文件、main 的 AGENTS.md 和下列现行规范。
2. 核对当前工作分支真实 HEAD 与本文内容提交；有差异时检查后续提交和 Actions，禁止覆盖或重复启动任务。
3. 用户要求继续时直接执行已定范围；只要求恢复时仅核对。GitHub 证据优先，不将本地文件或未结束运行当成完成。
4. 每个可恢复小任务先保存到工作分支，回读确认，再更新 main 本入口；非强制提交，并发时重新读取整合。

## 当前任务（2026-09-18）
- 用户明确：2018 及以前完成，接着生产 **2019—2024**；只汇报关键进度和异常。
- 当前工作分支：`c-mode-v2-2019-2024-production`。
- 核实到的内容提交：`989caf507be597cbac56747ed20add8f12227e84`（初始化新批次清单和源文件登记）。
- 基线内容分支：`c-mode-v2-2013-2018-production`，HEAD `95208fcaaeb38907547f64e7d46322bd8caee077`。
- 批次清单：`batch-manifests/2019-2024.json`，每年 cloze、text1—text4、partb、translation，共 42 篇，当前 draft。
- 2019：正文、逐句翻译、演员/韵律、词汇及双语映射正在制作，尚未保存可宣称完成的内容。
- 2020—2024：待制作。六年原卷已找到；2024 未随本轮附件挂载，已通过用户已有文件找回，其持久标识为 `libfile_fa8f9ed28b30819184b4677bc515eb0a`，名称 `2024年考研英语二真题【可复制搜索查词】.pdf`。新分支初始源登记中的 2024 locating_original 已过时，下一次内容检查点更新。
- 已执行：V2 基础回归 54 项通过。尚未正式全批校验、冻结、音频生成或发布。
- source_ref 目前指向基线，全部源稿保存后必须更新至完整源稿提交，不能直接用基线冻结。

## 已完成旧批次的核实证据
- 旧入口停留于 2017 候选稿，是过期快照；禁止据此重做 2013—2018。
- `gh-pages:reports/production-v2-release.json` 记录 2013—2018 为 published，完整状态链；freeze_id=`6ab366587c9c892df47439c75153836c0db41cfe2c2a6d97ad681c3617caf8a6`，previous_production_sha=`b56b6d5c89119ca36bc0a4459cc238125d2bc09e`。
- [旧批次发布恢复运行](https://github.com/dannhitruong852-jpg/taptap/actions/runs/35312922210)：success。
- 已核实生产 HEAD：`bb1bc2028267128e5a67d7eb7f99268d0a8517f0`。
- [对应 Pages 部署](https://github.com/dannhitruong852-jpg/taptap/actions/runs/35312961037)：输入同一生产 SHA，success。
- 旧入口要求核对的运行 35250800974 已 success，当前没有该旧运行并发冲突。
- 旧发布报告 source_ref 仍为早期值；这里只记录实际证据，不为旧报告追认其精确内容来源。

## 现行规范与下一步
- `PRODUCTION_RULES.md`
- `docs/production/C_MODE_PRODUCTION_V2.md`
- `docs/superpowers/specs/2026-09-17-c-mode-production-pipeline-v2-design.md`
- 内容/声音总纲：`docs/superpowers/specs/2026-09-12-kaoyan-c-batch-production-design.md`。
- 原 PDF 是正文依据；每年七篇；剔除题干/选项/作文；完型还原空格；逐句信达雅翻译；15 演员按文章适配、C 总纲适配、同等适配下的负载均衡选角。
- 先完成 2019 样本并按现有 V2 校验，再完成其余年份；每年保存 reviewed candidate 和可追溯 QA，不伪造审核。
- 源稿齐备后更新 source_ref，使用同一 canonical V2 workflow：draft → validated → frozen → rendering → merged → release_candidate → published。冻结前禁止大规模音频生成。
- 首次 publish=false；发布必须保留当前所有年份/文章，以当前 gh-pages 为基线追加，保留回滚元数据，核对同 SHA Pages 成功后才称已发布。
- 已成功产物复用，仅重试失败/缺失单元；不创建每批次专用 once 工作流，不绕过失败门禁。

## 保存协议
成果提交到工作分支并确认远端后，将内容 SHA、校验结果、阻塞和下一步更新至 main 本入口。这是两次提交，不具有原子性。main 纯文档提交可用 [skip ci] 避免旧 APK 构建；不可绕过内容/代码真实验证。所有推送非强制，并发先合并最新状态。临时绝对路径不保证跨窗口可用。此协议没有自动锁、自动保存或突然中断恢复保证。
