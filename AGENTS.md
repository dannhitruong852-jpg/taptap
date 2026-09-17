# 英语真题项目：跨窗口接手规则

用户固定口令：
> 请读取 GitHub 仓库 dannhitruong852-jpg/taptap 的 main 分支根目录 PROJECT_STATUS.md，按其中的接手流程恢复最新项目状态。

## 先定位项目

这是多分支仓库。main 目前仍含旧安卓应用和工作流入口，英语真题的当前工作分支由 [PROJECT_STATUS.md](https://github.com/dannhitruong852-jpg/taptap/blob/main/PROJECT_STATUS.md) 指定。不要根据 main 的 app 目录推断英语项目的进度。

任何英语真题接手会话都应先读取 main 的 PROJECT_STATUS.md，并按其中的接手流程核对当前远端 HEAD、任务记录和相关产物。只读取本地旧副本不足以确认最新状态。

## 持续保存

每完成一个可恢复的小任务、遇到阻塞或结束本轮时：
1. 将成果保存到指定工作分支，核对远端提交。
2. 更新 main 的 PROJECT_STATUS.md 中的最新内容 SHA、已核实结果、未完成部分、阻塞及下一步。
3. 非强制提交，回读确认；并发时先整合他人的更新。
4. 不把仅存在本地的文件、已启动但未结束的任务或基础检查通过写成最终完成。
5. 文档维护按 PROJECT_STATUS.md 第 6 节执行。当前没有自动保存服务或强制更新门禁，不得假定无需执行更新。

## 指令与范围

用户当前要求优先。只要求恢复状态时完成只读核对；要求继续时执行既定下一步。恢复文档不能自行扩大授权或替用户批准发布。

产品原则和生产流程以当前工作分支的 PRODUCTION_RULES.md、docs/production/C_MODE_PRODUCTION_V2.md 和现行设计为准。旧 handoff 可查历史需求，其旧进度不得覆盖新的仓库证据。
