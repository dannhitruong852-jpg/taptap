# 考研英语真题 C 模式学习网站——任务交接文档

日期：2026-09-12  
用途：供新的 ChatGPT / Codex / 开发会话无缝接手当前项目。  
原则：以 GitHub 当前代码和 commit 为事实依据；本文件记录产品决策、已知状态、未完成事项和接手顺序。

---

## CURRENT STATE — 新模型优先读取

当前开发分支：`kaoyan-reader-v1`。

交接时记录的 HEAD：`d11aefc2e21cd04f8364a7f690541d2c776bc6b3`，commit message：`test: cover multi-year PDF extraction quirks`。接手时必须重新核对当前 HEAD，不要假设本文件永远最新。

项目已经有一个能在线工作的 **2002 Text 1 Chatterbox 技术样片**；C 模式正式设计 spec 和实施 plan 已经落库。Task 1（schema + C validator）基本完成；Task 2（PDF extractor + synthetic tests）代码已经写出，但交接时最新 HEAD 尚没有完整 CI 证据，也还没有对真实 2000–2026 年 PDF 做系统 dry-run 验证。

Task 3–8 尚未完成。当前第一优先级不是继续堆功能，而是：

1. 跑 content / voice / site tests；
2. 建立 combined CI；
3. 对真实年度 PDF 做 extraction dry-run；
4. 确认 extraction 可靠后再进入 cloze reconstruction；
5. 之后再解决 enrichment（信达雅翻译、词汇等级、C 语义导演）、正式 actor reference、catalog、通用 batch TTS 与全量 Actions。

不要重新讨论已经确认的 C 总纲、演员分配原则、GitHub 普通开发权限和 Chatterbox 技术路线。不要声称“全量任务已经在后台跑”；交接时全量 20 多年批处理 GitHub Actions 尚未创建并启动。

新会话推荐先做只读校准：读取本文件、C batch spec、C batch plan，核对 HEAD / 最近 commits / 当前 tests；确认事实后再继续开发。

---

## 0. 接手时最先读这一段

这是一个已经有可运行样片、但全量批处理系统还没有做完的项目。

不要从头设计，也不要重新和用户讨论声音原则、演员分配、是否使用 Chatterbox、网站要不要上传 PDF 等问题——这些都已经确定。

接手后应先读取仓库里的两份最新文件：

- `docs/superpowers/specs/2026-09-12-kaoyan-c-batch-production-design.md`
- `docs/superpowers/plans/2026-09-12-kaoyan-c-batch-production.md`

交接时记录：最新 C 模式设计提交为 `89bd0ca19fcf2ff2c69b04066ff467a14875bafe`；实施计划提交为 `ebf35844851ba8acffe11b04afd3cea530f13f85`。

最重要的一条：**不要声称“全量任务已经在后台跑”**。目前全量 20 多年批处理 GitHub Actions 尚未创建并启动。

---

## 1. GitHub 当前状态

仓库：`dannhitruong852-jpg/taptap`

仓库目前为 public。

开发分支：`kaoyan-reader-v1`

交接时记录的开发分支 HEAD：

`d11aefc2e21cd04f8364a7f690541d2c776bc6b3`

commit message：

`test: cover multi-year PDF extraction quirks`

交接时该 HEAD 没有 GitHub commit status/check 记录，因此不能称为“CI 全绿”。

线上 GitHub Pages 分支：`gh-pages`

交接时线上 HEAD：

`24e3ff7341011d21d4eea311b27b0cffe0af1ae1`

commit：

`feat: publish 2002 Text 1 Chatterbox audio`

线上网址：

`https://dannhitruong852-jpg.github.io/taptap/kaoyan-reader-v1/`

线上目前本质上仍是 **2002 Text 1 技术样片**，不是全量多年版本。

用户已经多次明确：GitHub 提交、分支、Actions、Pages 等普通开发操作已授权，不要反复询问。

---

## 2. 用户最初想解决什么

用户在备考考研英语，希望把二十多年真题做成一个非常简单的手机学习网站。

核心痛点不是“刷题”，而是把真题文章变成方便阅读、理解、听读和记词的学习材料。

用户使用 Android / vivo 手机，希望：

打开一个网址 → 选年份 → 选题型/文章 → 看英文和中文 → 看重点词 → 点播放。

不希望：上传文件、注册服务、配置模型、买 TTS API、反复授权、自己整理 PDF。

---

## 3. 最终目标

把已有年度真题 PDF 离线预处理成一个静态学习网站。

理想完整流程：

PDF → 目标正文提取 → 完型还原 → 切句 → 信达雅中译 → 词汇 1–9 级 → C 模式导演 → 自动选演员 → Chatterbox 生成音频 → QA → 静态网站 → GitHub Pages

网站运行时：

- 不生成 AI 内容；
- 不实时 TTS；
- 不调用商业 API；
- 只读取 JSON 和静态音频。

---

## 4. 用户已经确认的内容范围

每张试卷只处理四类英文正文。

### 4.1 完型填空 / Use of English

只保留完型文章正文，但不能保留空格。必须根据正确答案把空补回去，恢复为一篇完整、正常可读、可朗读的文章。

A/B/C/D 选项只允许在生产阶段用于恢复文章，绝不能出现在最终网站。

### 4.2 阅读理解 Part A

只保留每一篇 Text 1 / Text 2 / Text 3 / Text 4 的文章正文。

不要：题干、问题、A/B/C/D、答案解析。

### 4.3 Part B / 新题型 / 七选五等

只保留真正需要阅读的文章正文。

不要：七选五备选项、小标题匹配备选项、人名匹配列表、问题、Directions。

### 4.4 Translation

只保留要求考生翻译的英文原文，不要题目说明。

### 4.5 完全不要做的内容

全部 Writing 忽略：小作文、大作文、图表、作文题目、范文。

也不要把答题说明、选择题选项、答案页混进网站。

这些规则已经写进 C 模式正式 spec。

---

## 5. PDF 来源

Project 中已有年度真题 PDF。

材料包括：

- 2000–2009：`2000年考研英语真题` … `2009年考研英语真题`
- 2010–2026：`2010年考研英语二真题` … `2026年考研英语二真题`
- 另有：`大纲词汇背诵宝典（英语二）.pdf`

词汇宝典只用来辅助词汇难度体系，不是试卷年份。

范围细节：早期用户最初以 2002 为样片起点，但 Project 实际已有 2000–2026 共 27 个年度文件。目前最新批处理 spec 写法是对“所有发现的年度试卷”进行处理。

因此接手时不要随口说“25 年”或“20 张”；应以实际文件库存为准。

---

## 6. 翻译标准

翻译标准已经确定为“信、达、雅”。

### 信

忠于原文。不能漏译、擅自增加意思、改变因果、改变否定、改变比较、错处理限定范围。

### 达

中文正常、顺畅，不要把英语句法生硬搬过来。

### 雅

在准确基础上，让中文顺、自然、好读、不拗口。

网站最终形式仍是英文句子和中文译句一一对应。

批量初译以后应有第二轮自审，重点检查：漏译、否定、比较、主从关系、代词指代、专有术语、生硬直译。

---

## 7. 词汇体系

用户确定的是 1–9 级词汇难度。

网站重点表现 6、7、8、9 级词汇；6 级及以上需要加粗/突出。

原则：

- 同一个词跨年份等级尽量稳定；
- 不根据某篇文章临时主观变难变易；
- 可以结合《大纲词汇背诵宝典》；
- 也可结合词频、超纲程度、词形复杂度和具体语境义。

目前这一部分还没有实现成真正的批量算法。

---

## 8. 最重要的声音原则：方案 C 总纲

正式名称建议保持：**理解导向的美式日常交流式朗读**。

这不是：有声书、新闻播音、纪录片、广播剧、教学慢速英语。

核心感觉：

> 一个真正读懂文章的美国人，面对面把这段内容讲给另一个人听。

目的首先是帮助理解，而不是炫技。

### C 总纲 8 条原则

1. **理解优先于表演**：声音必须帮助听者听出重点、逻辑、结构、态度、含义。
2. **每一句都有自然语气**：旁白绝不等于平读。即使标记为 neutral，仍然必须有自然重音、停顿、轻重、句尾走势、信息焦点。`neutral ≠ robotic/flat`。
3. **角色稳定，韵律持续变化**：同一篇文章主讲人尽量稳定；不能为了制造丰富感频繁换演员。主要通过重音、节奏、语速、音高、停顿、态度制造变化。
4. **固定导演判断顺序**：语义理解 → 话语功能 → 信息焦点 → 逻辑关系 → 韵律曲线 → 情绪/强度 → 速度/停顿/重音。不能先随便贴 warm/serious 标签。
5. **微反差密度**：任意连续大约 2–3 句，应至少出现一个可感知、但克制的小语气波峰。目前硬 validator 为任意连续 3 句不能全部是 `low`，至少一个必须为 `micro` 或 `strong`。
6. **强表演必须有文本依据**：只有直接对白、强转折、讽刺、笑点、冲突、强评价、明显惊讶等情况才允许明显加强，不能为了“好听”乱演。
7. **一句话内部也允许变化**：长句不能整句只有一个情绪标签，应根据语义转折、动作和信息焦点调整节奏、重音和语气。
8. **正常美国人自然交谈速度**：不是教学慢速。复杂地方自然稍慢，简单/动作/轻松地方自然稍快。

C 模式机器配置已写入 `voice-pipeline/config/c_mode.json`，包括：

- `default_accent = en-US`
- `pace = natural_conversational`
- `max_low_contrast_run = 2`
- `narration_is_never_flat = true`
- `strong_acting_requires_textual_evidence = true`
- 默认 rate 约 `0.92–1.06`
- 硬范围 `0.80–1.10`

---

## 9. 15 名演员体系

用户已经明确：演员以后由 ChatGPT 自己分配，不需要再讨论，不需要逐篇确认。

现有 15 槽位：

| ID | 人格定位 |
|---|---|
| 01 | 理性思想型男声 |
| 02 | 学术解释女声 |
| 03 | 纪录片型男声 |
| 04 | 冷静纪录片女声 |
| 05 | 演讲/交流型男声 |
| 06 | 年轻自然女声 |
| 07 | 温暖故事女声 |
| 08 | 科技/干幽默男声 |
| 09 | 权威评论男声 |
| 10 | 锐利评论女声 |
| 11 | 少女/儿童感角色声 |
| 12 | 青年男性角色 |
| 13 | 年长男性角色 |
| 14 | 成熟英式男声 |
| 15 | 清晰英式女声 |

过去用过 Peter Thiel、Natalie Portman、Morgan Freeman、Steve Jobs 等姓名来描述气质方向。这些名字只能作为声音气质锚点，绝不能克隆名人、冒充名人或做可识别真人声纹复制。

正式参考音必须来自许可明确、可长期保存、清晰、可处理、无背景音乐、无多人重叠的合法素材。

11 号“少女”角色也不要使用真实未成年人未经适当授权的素材，可以使用成年表演者或合法生成的 childlike register。

演员系统回答“谁在说”；C 总纲回答“他应该怎么说”。

普通文章原则上 1–4 个演员。只有真正说话者改变、直接对白、明确人物引用时才优先换声。文章情绪改变本身不等于换演员。

---

## 10. TTS 技术路线

技术路线已经锁定：**Chatterbox**。

生产链路不使用：Google TTS、商业按字收费 TTS、商业按分钟收费 TTS、浏览器 `speechSynthesis`、Kokoro。

使用原版英文 Chatterbox，因为支持 voice reference、CFG、exaggeration，更适合当前导演参数。

运行方式为预生成静态音频，网站只播放文件，因此运行时 TTS 成本目标为 0。

---

## 11. 已经完成的 2002 Text 1 技术样片

当前网站已经成功完成过 2002 Text 1。

原文 21 句；由于句内角色切换，最终拆成 24 个音频 segment。

主要分配：

- actor 05：主叙述
- actor 12：天堂新来者
- actor 13：St. Peter

例如第 9 句：`Who is that?` → actor 12；narration → actor 05。

第 10 句：`Oh, that's God` → actor 13；`came the reply` → actor 05；punchline → actor 13 / ironic / intensity 2。

技术结果：Chatterbox 全 24 段生成成功。

旧完整生成 run：`34623362146`

之后发布 run：`34625384493`

成功发布到 `gh-pages`。

但这不是艺术验收通过版。用户试听后明确提出核心问题：

> 除了对白有点语气，旁白几乎都很平。

因此 2002 当前音频只能视为工程技术样片，不是 C 模式最终合格音频。未来最好重新按 C 模式导演并生成 2002。

---

## 12. 2002 Text 1 还有一个原文忠实度问题

当前：`kaoyan-reader-v1/content/2002/text1.json`

已知有几个标点/字符细节与 PDF 原文不完全一致。

例如 sentence 4：当前类似 `alternatively, if`，PDF 原文为 `alternatively if`，多了一个逗号。

另外部分 ASCII apostrophe 与 PDF curly apostrophe 不一致，例如：

- `nurses'` vs `nurses’`
- `it'll` vs `it’ll`
- `chairman's` vs `chairman’s`
- `mustn't` vs `mustn’t`
- `it's` vs `it’s`

在最终声称“原文完全忠实”之前应修。第 4 句多出来的逗号甚至可能影响当前音频停顿。

---

## 13. 网站目前已经具备的能力

目录：`kaoyan-reader-v1/`

主要已有：

- `index.html`：页面骨架和播放器 shell
- `styles.css`：移动端样式，米白/浅色阅读背景、圆角卡片、英文 serif、中文灰色 sans-serif、手机优先
- `app.js`：加载 2002 Text1 JSON、加载 manifest、渲染中英、标重点词、播放静态音频、自动下一句
- `playback.js`：纯播放队列逻辑，segment 顺序、速度、上一句/下一句边界
- `audio-player.js`：基于 `HTMLAudioElement`，支持 play、pause/resume、stop、sentence 内多 segment 连播、error handling
- `scroll-behavior.js`：向下滚动底部播放器完全隐藏；向上滚动快速恢复。以前有过 bug，后来通过 `<aside id="player-shell">` 修过

播放器现有功能：播放/暂停、上一句、下一句、replay、当前句高亮、0.85x、1x、1.15x。

后续不能因为做年份导航而破坏这些能力。

---

## 14. 声音参考源的现状

当前只为工程 pilot 准备了几个 CMU ARCTIC 参考声。

使用 Hugging Face mirror：`MikhailT/cmu-arctic`

工程映射：

- actor05 → BDL，美国男性
- actor12 → JMK，加拿大男性
- actor13 → RMS，美国男性

注意：这只是工程验证音色，并不是最终 15 演员完整演员库。

正式目标之前设计成约 65 段参考音：主要演员约 5 条/人，辅助演员约 3 条/人，角色演员约 4 条/人。

目前这个 65 段正式 reference pack 没有完成，所以现在直接把全 15 演员应用到全量年份 TTS，会缺真正的 reference source。

---

## 15. 新 C 模式批量系统目前完成到了哪里

正式实施计划一共有 8 个任务。

### Task 1：Canonical schema + C validator

基本完成。

新增：`voice-pipeline/tests/test_batch_schema.py`

commit：`744995d95e43fc84a17e87b5432bdd9f3e581b0a`

测试覆盖：section type、actor 01–15、intensity、rate、3 句微反差、C mode config。

`voice-pipeline/batch_schema.py`

commit：`45dc348f9d8bf90ea56cbf9f53185c6f947fe012`

已定义允许 section：

- `cloze`
- `reading`
- `part_b`
- `translation`

演员：01–15。

情绪：`neutral`、`warm`、`lively`、`serious`、`curious`、`ironic`、`tense`、`emotional`。

contrast：`low`、`micro`、`strong`。

以及文章、句子、segment 必要字段。

rate 硬限制：`0.80–1.10`。

3 句窗口全部 `low` 会报错。

`voice-pipeline/config/c_mode.json` 见前文。

---

## 16. Task 2：PDF 提取

已经写了主要代码和测试，但尚未完整验证。

`content-pipeline/normalize.py`

commit：`95c4e2ff882b0078507d790a6a36d7e93e414a4c`

作用：统一换行、删除 form feed、清除部分页码噪声、合并 PDF 错误换行、保留段落、修复部分行末连字符。

`content-pipeline/extract_exam.py`

commit：`533725d92accb6e8c732418ac1817066ea7034e2`

目前尝试兼容：

- Section I Use of English
- OCR 错误 `Use o f English`
- Section II Reading Comprehension
- Part A/B/C
- Text headings
- fullwidth 字符
- `T e x tl`
- Section HI Translation
- 没有 Part B 标题但 q40 后有 Directions
- Part B candidate option 删除
- 41–45 空位标记删除
- pre-2005 translation
- 2005–2009 Part C translation
- Writing 截止

`content-pipeline/tests/test_extract_exam.py`

交接时当前 dev HEAD：`d11aefc2e21cd04f8364a7f690541d2c776bc6b3`

包含大量 synthetic fixture 测试：normal wrapping、2010+、2005–2009、pre-2005、duplicate answer key、fullwidth、OCR spacing、Part B choices、HI Translation、missing Part B heading、broken option brackets、old question 11 等。

**重要：**这些最新 content-pipeline 测试目前没有 GitHub CI 证据证明在 d11 HEAD 上通过。

之前想新增 `.github/workflows/reader-pipeline-checks.yml`，但工具调用过程中被打断。交接时核对该文件并没有成功写进分支，GitHub fetch 返回 404。

因此不要误以为“最新提取器已经 CI 全绿”。

---

## 17. Task 3–8 当前状态

### Task 3：完型自动还原

没做。

计划文件：`content-pipeline/cloze.py`

目标 API：`fill_cloze(article_text, answers, choices)`

必须使用可信 answer key 恢复；找不到正确答案时标记 `needs_answer_key`，绝不能猜。

### Task 4：Article builder + C director

没做。

计划文件：

- `content-pipeline/build_articles.py`
- `content-pipeline/director_c.py`
- 对应 tests

需要真正产生：句子、中译、vocab、discourse function、prosody focus、contrast、actor、segments。

### Task 5：网站多年份 catalog

没做。

当前网站还是写死/面向单篇。

目标需要：`content/catalog.json`，以及年份选择、题型选择、文章选择。

不能破坏现有播放器。

### Task 6：通用批量 Chatterbox renderer

没有完成。

以前 pilot 已有 `voice-pipeline/batching.py`，包括 deterministic partition/shard helpers，可复用。

但 `generate_batch.py` 尚未实现。

### Task 7：并行全量 Actions

没做。

计划中的：

- `.github/workflows/generate-kaoyan-batch.yml`
- `.github/workflows/publish-kaoyan-batch.yml`

都没有创建。

所以目前没有任何“20 多年自动后台生成”任务在跑。

### Task 8：全量年份生成

没开始。

完整年份成品目前为 0 个完整年度；已有 2002 Text 1 一篇旧工程 pilot。

---

## 18. 一个非常重要的架构缺口：翻译和 C 导演并不能凭空在 Actions 里自动完成

之前讨论时曾经把流程描述得过于“自动化”：

PDF → translation → director → TTS

但现在代码实际上只实现了确定性的提取、schema、部分 TTS 技术。

以下内容目前没有自动模型负责：

- 信达雅翻译
- 文章人格判断
- discourse function
- prosody focus
- C 模式语义导演
- 1–9 词汇难度

由于用户又明确要求不买商业 API、不在运行时用 AI API，因此接手模型必须认真处理这个问题。

推荐思路：**语义 enrichment 在 ChatGPT/Codex 工作阶段预生成成 JSON；GitHub Actions 只负责验证 + TTS + 发布。**

不要假装一个纯 Python regex 程序可以自动完成高质量“信达雅”和语义导演。

---

## 19. 已尝试但失败的方法

### 19.1 浏览器 speechSynthesis

最开始网站考虑直接使用浏览器系统 TTS。用户的 vivo/Android 浏览器不支持/无法正常使用，因此已废弃。后续不要重新走浏览器 TTS。

### 19.2 Festvox CMU ARCTIC 下载

GitHub Actions 第一版从 Festvox 下载参考音失败：`curl: (7) Failed to connect to festvox.org:443`。

因此改用 Hugging Face mirror，后来 Chatterbox pilot 成功。

### 19.3 本地/container 安装 Chatterbox

容器曾尝试 pip install，因为 Python package/DNS/Internet 环境问题失败。

GitHub Actions 有网络，已经证明可以使用 Python 3.11、ffmpeg、pip Chatterbox、下载模型、生成 Opus。

所以重型 TTS 推荐继续放 GitHub Actions。

### 19.4 Sharding TDD 的一次故意失败

commit：`b13e5654b4579a8163c66c8b84c3dd1e4b057c53`

run：`34624710301`

失败原因：test 要求 `select_shard`，实现还不存在。这是 TDD 的 RED，不是遗留 production bug。

之后 commit：`ae3f1eae118ed027ef27afcd32c3e010233966bd`

实现 `select_shard`。

run：`34624879043`，成功。

---

## 20. 目前已知测试结果

### 已验证成功

Voice pipeline unit tests：

- run：`34630487444`
- HEAD：`744995d95e43fc84a17e87b5432bdd9f3e581b0a`
- 结论：success

Chatterbox smoke test：

- `34630487160`
- `34630501109`
- `34630515468`

结论均为 success。

2002 Text1 generator 在 C config commit 后也重新触发过：

- run：`34630515493`
- 结论：success

但请注意：它仍然是旧的 2002 Text1 generator。成功不代表新 C director 已完成、新 PDF extractor 已验证或全量流程已经成功。

---

## 21. 目前没有验证的东西

尚未真正验证：

1. `content-pipeline/tests/test_extract_exam.py` 在最新 d11 HEAD 的 CI 结果；
2. 真实 2000–2026 PDF 是否全部能正确分段；
3. 是否会有题干/答案/选项混入正文；
4. 所有年份完型是否能正确恢复；
5. 全量信达雅翻译；
6. 1–9 vocab 分级；
7. C 模式 director 的真正语义效果；
8. 15 actor 完整 reference library；
9. 真实多年 TTS generation；
10. 全量 fail-soft retry；
11. full ASR QA；
12. speaker consistency QA；
13. 全量 clipping / silence / truncation QA；
14. Opus 在用户 vivo 浏览器上的最终兼容性；
15. 多年份网页导航；
16. full batch deploy。

当前音频 manifest 里的 `qa_status = candidate`，因此不要说“production QA passed”。目前没有依据。

---

## 22. 当前最核心的问题，不是某一个 bug

当前真实状态：

> 技术 vertical slice 已经成功，但从一篇升级到多年生产系统只完成了前两层基础设施。

主要 gap：

- **Gap A**：真实 PDF 提取尚未系统验收
- **Gap B**：完型恢复尚未实现
- **Gap C**：高质量翻译没有生产方案落地
- **Gap D**：C 模式语义导演没有实现
- **Gap E**：词汇等级算法没有实现
- **Gap F**：15 actor 正式参考声库没有建立
- **Gap G**：网站仍只有单篇
- **Gap H**：全量 batch Actions 未创建

---

## 23. 下一步具体应该做什么

建议严格按以下顺序。

### 第一阶段：先验证当前代码，而不是马上继续堆功能

先在隔离 worktree 或 CI 跑：

```bash
PYTHONPATH=content-pipeline python -m unittest discover -s content-pipeline/tests -v
PYTHONPATH=voice-pipeline python -m unittest discover -s voice-pipeline/tests -v
cd kaoyan-reader-v1 && npm test
```

建立一个真正的 combined workflow。

注意：之前想创建 `reader-pipeline-checks.yml`，但它没有落库。

### 第二阶段：用真实 PDF 做 extraction dry-run

不要只相信 synthetic tests。

对每一个实际年份输出报告，例如：`reports/extraction/2000.json` … `reports/extraction/2026.json`。

报告至少包括：

- source filename
- source hash
- cloze count
- reading count
- part_b count
- translation count
- warnings
- suspected contamination
- unresolved sections

对提取正文做 spot checks，特别检查 `[A]` 等是否残留、question 21/11 等是否残留、Writing 是否残留、answer explanation 是否残留。

### 第三阶段：实现 cloze reconstruction

严格 TDD。

必须使用正确答案和对应 choice。无法证明答案时标记 `needs_answer_key`，而不是猜。

### 第四阶段：解决 enrichment 架构

生成：中译、vocab、discourse function、prosody focus、contrast、article personality、actor、C segment。

建议由 ChatGPT/Codex 批量预计算 JSON，然后 GitHub Actions 只消费确定性 JSON。

### 第五阶段：把正式 actor reference pack 做好

不能直接用现在 3 个 CMU 声音假装 15 actor 已完成。至少先建立 15 个 actor 的稳定合法 reference，再开始真正大规模 TTS。

### 第六阶段：先做一个多类型 canary

不要一上来生成 27 年。

建议至少包含：1 篇完型、1 篇学术阅读、1 篇故事/人物阅读、1 篇 Part B、1 篇 Translation、1 篇带 dialogue/irony 的文章。

检查 C 模式是否确实解决“旁白平”的问题。

### 第七阶段：catalog

做好 `year → section → article` 的 UI，保持当前播放器逻辑不变。

### 第八阶段：general batch TTS

做 `generate_batch.py`，支持 fingerprint、cache、shard、retries、fail-soft、partial artifact。

### 第九阶段：GitHub Actions

再创建：

- `generate-kaoyan-batch.yml`
- `publish-kaoyan-batch.yml`

先跑 canary，拿到真实运行时间后才能估算全量耗时。

---

## 24. 关于时间估算：不要重复之前的错误

此前助手曾经先说 12–24 小时，后来又说 4–8 小时，最后已经明确收回这个估计。

原因：当时全量流水线根本没有跑通，因此这些时间没有实测依据。

新的 ChatGPT 不要再随口承诺“4 小时”“明早肯定完成”“后台已经在跑”。

正确做法：先跑一个真实多文章 canary → 得到文章数、segment 数、每 shard 时间、失败率 → 再估算。

---

## 25. 关于“后台工作”尤其不能说错

ChatGPT 本身不能在对话停止后继续自主思考、修代码。

只有真正触发的 GitHub Actions 可以独立继续运行。

所以只有在已经有真实 run ID 后，才能说“GitHub 正在后台跑”。

交接时不存在全量批处理 run ID。

不要告诉用户“你睡觉它会自己把 27 年做完”。

---

## 26. Fail-soft 原则

用户已经明确希望：如果单个地方出错，不要马上停下来反复问他。

应：自动修能修的；自动 retry；修不了就隔离；其他年份继续；最后统一补洞。

用户希望的工作模式：

> 全量推进 → 局部失败隔离 → 继续 → 最后集中修

只有出现真正硬阻塞才打断用户，例如：PDF 缺页、原文无法判断、要引入付费服务、要做高风险不可逆仓库操作、出现全新且会改变整个产品方向的重大决定。

普通测试失败、路径错、GitHub Actions fail、某音频 fail、某年份 regex 不匹配，都应该自己诊断处理。

---

## 27. 现有旧文件体系

### Website

- `kaoyan-reader-v1/index.html`
- `kaoyan-reader-v1/styles.css`
- `kaoyan-reader-v1/app.js`
- `kaoyan-reader-v1/scroll-behavior.js`
- `kaoyan-reader-v1/playback.js`
- `kaoyan-reader-v1/audio-player.js`
- `kaoyan-reader-v1/package.json`
- `kaoyan-reader-v1/tests/content-schema.test.js`
- `kaoyan-reader-v1/tests/playback.test.js`
- `kaoyan-reader-v1/content/2002/text1.json`
- `kaoyan-reader-v1/audio/2002/text1/manifest.json`
- 24 个 `.opus`

### Voice pipeline

- `voice-pipeline/config/actors.json`
- `voice-pipeline/config/emotions.json`
- `voice-pipeline/config/c_mode.json`
- `voice-pipeline/references/sources.json`
- `voice-pipeline/render.py`
- `voice-pipeline/qa.py`
- `voice-pipeline/generate_text1.py`
- `voice-pipeline/batching.py`
- `voice-pipeline/batch_schema.py`
- `voice-pipeline/requirements.txt`
- 各类 tests

### Current content pipeline

- `content-pipeline/normalize.py`
- `content-pipeline/extract_exam.py`
- `content-pipeline/tests/test_extract_exam.py`

---

## 28. 当前 GitHub workflows

现有旧 workflows 主要有：

- `.github/workflows/build.yml`
- `.github/workflows/chatterbox-smoke.yml`
- `.github/workflows/generate-text1-pilot.yml`
- `.github/workflows/publish-text1-pilot.yml`
- `.github/workflows/voice-unit-tests.yml`

交接时不存在：

- `generate-kaoyan-batch.yml`
- `publish-kaoyan-batch.yml`

也不存在最终成功落库的：

- `reader-pipeline-checks.yml`

不要想当然认为它们已经建了。

---

## 29. 用户交互偏好

用户不喜欢：

- 每做一步都问确认；
- GitHub 反复授权；
- 演员每篇问一次；
- 明明原则定好了又从头讨论；
- 模板化重复解释。

用户希望：规则先确定一次，然后 ChatGPT 自己判断并执行。

尤其：

- C 总纲不再讨论，除非用户主动要改；
- 演员分配不再讨论，由系统/ChatGPT自己决定；
- GitHub 普通写操作不再授权，已经授权；
- 局部故障不应阻塞全局，自己处理。

---

## 30. 最容易重复犯的错误

新的 ChatGPT 尤其不要犯以下错误：

1. 把旁白理解成 `neutral = 平读`；
2. 每篇用很多演员制造“丰富感”；
3. 用换演员代替语气变化；
4. 把 C 模式做成戏剧化广播剧；
5. 把速度做成教学慢速；
6. 把问题和 A/B/C/D 搬进网站；
7. 把 Part B candidate list 当成文章；
8. 忘记完型必须补完整；
9. 把作文也做进去；
10. 使用浏览器 `speechSynthesis`；
11. 引入 Google TTS；
12. 引入收费 TTS；
13. 重新建议 Kokoro；
14. 把当前 2002 candidate 音频说成 C 模式最终样片；
15. 把名人气质锚点理解成名人克隆；
16. 声称 ASR/speaker QA 已经做完；
17. 声称当前 d11 HEAD CI 全绿；
18. 声称全量 batch 已经启动；
19. 在没有真实 benchmark 的情况下再次承诺 4–8 小时；
20. 一个局部 failure 就停下来找用户；
21. 改年份导航时把原来的移动端播放器交互破坏掉；
22. 忽视 2002 原文标点 fidelity 问题。

---

## 31. 当前状态一句话总结

现在已有一个能在线工作的 2002 Text 1 静态 Chatterbox 技术样片，也已经把 C 总纲和多年 PDF 抽取框架写进开发分支；但全量工程目前仍停在“Task 1 基本完成、Task 2 已写代码和测试但尚未真实 CI/全 PDF 验证”的阶段，完型恢复、翻译、词汇分级、C 语义导演、多年份 UI、15 演员正式 reference、通用 TTS batch、全量 Actions 与最终部署都还没有完成。

---

## 32. 给新 ChatGPT 的推荐第一句话

新对话接手以后，建议先这样理解任务：

> 不重新设计产品，不重新询问已经确认过的 C 总纲/演员/GitHub 权限。我先读取 `kaoyan-reader-v1` 当前 HEAD、本交接文档、C batch spec 和 plan，先验证现有 content/voice/site tests，再对真实年度 PDF 做可追踪 extraction dry-run；只有拿到真实通过/失败数据之后再继续 Task 3，不把未经验证的状态称为完成。

### 推荐的新窗口第一条实际指令

> 这是这个项目的完整交接文档：`docs/handoff/2026-09-12-kaoyan-project-handoff.md`。先不要修改代码，也不要开始开发。第一轮只做接手校准：读取本文件的 `CURRENT STATE`、第 0、1、23、31、32 节；再读取 `docs/superpowers/specs/2026-09-12-kaoyan-c-batch-production-design.md` 和 `docs/superpowers/plans/2026-09-12-kaoyan-c-batch-production.md`；最后核对当前分支 HEAD 和最近 commits。完成后只告诉我：你理解当前项目做到哪里、当前最先应该验证什么、交接文档与仓库实际状态有没有明显冲突。不要修改任何代码，完成这一轮后停下来。

---

## 维护规则

每完成一个明显阶段后，更新本文件的 `CURRENT STATE`、HEAD、已完成/未完成事项和下一步。不要为了保留历史而不断把正文无限追加；长期历史应由 Git commit 记录，本文件负责保存“现在接手需要知道的事实”。
