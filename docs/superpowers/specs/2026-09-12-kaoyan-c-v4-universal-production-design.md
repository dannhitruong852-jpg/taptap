# 考研英语真题 C v4 通用声音生产系统设计

日期：2026-09-12  
适用范围：2000–2026 考研英语真题阅读型内容及后续年份  
状态：已完成方向确认，待用户复核书面规范后进入实施计划

## 1. 最高总纲

C 模式的最高原则只有一句：

> 一个真正理解文章的美国人，坐在你面前，把这篇文章讲给你听。

这不是“好听 TTS”目标，也不是“情绪越多越好”。它要求三件事同时成立：

1. **理解正确**：朗读行为必须建立在对文章主题、作者态度、论证结构、叙事结构和信息焦点的理解上。
2. **人物合适**：必须先判断“什么样的人最适合讲这篇文章”，再从演员池选择演员，不能反过来因为某个演员声音好就让大量文章迁就他。
3. **表达自然**：演员必须像真人交流，而不是新闻播报、课文朗读、广播剧或教学慢速英语。

固定生产顺序：

**文章理解 → 文章人格 → 演员匹配 → 演员标定 → 全篇导演 → 逐句/逐语义导演 → 声音生成 → QA → 最终音频 → 逐词时间轴 → 双语播放器。**

任何后续年份不得绕过这条链路。

---

## 2. 普适性原则

2002 不是孤立项目，而是 2000–2026 全量生产的母版。因此每一次改动都必须满足：

> 如果把同一规则用于 2003、2010、2024、2026，是否仍然成立？

只对单篇文章有效的手工补丁不得进入正式生产架构。

需要长期复用的能力包括：

- 文章人格分析
- 演员池与演员标定
- 通用导演语义
- 演员适配器
- Chatterbox 生成策略
- 三层 QA
- 最终音频逐词强制对齐
- 双语语义映射
- 通用播放器

---

## 3. 文章决定演员

### 3.1 Article Voice Profile

每篇文章进入 TTS 之前，必须先生成 `Article Voice Profile`。该结构至少包含：

- `domain`：经济 / 科技 / 医学 / 心理 / 社会 / 文化 / 叙事等
- `author_stance`：解释 / 分析 / 评论 / 劝告 / 讽刺 / 怀疑 / 讲故事等
- `formality`
- `narrativity`
- `humor_level`
- `rationality_emotionality`
- `baseline_mood`
- `speaker_persona`
- `preferred_age_impression`
- `preferred_gender_if_relevant`
- `dialogue_roles`
- `article_arc`

演员匹配只能读取这些文章属性，不能读取“哪个演员最近生成效果最好”作为主导条件。

### 3.2 选角规则

选角依据按优先级：

1. 文章人格匹配
2. 演员已通过真人感质量门槛
3. 演员擅长该类表达
4. 文章内部主讲人连续性

05 号演员目前是第一个被用户明确认可的高质量样本，但它的身份是 **Benchmark（质量基准）**，不是 Default Narrator（默认主讲人）。

---

## 4. 统一导演语言，而不是统一模型参数

### 4.1 通用导演层

文章和句子数据只描述“要表达什么”，不能直接写死某个模型参数。

通用导演意图包括但不限于：

- `neutral_explain`
- `warm_explain`
- `serious_analysis`
- `curious_probe`
- `restrained_irony`
- `narrative_build`
- `action_acceleration`
- `contrast`
- `qualification`
- `information_peak`
- `punchline`
- `conclusion_landing`
- `quoted_character`

每个导演单元同时可携带：

- `discourse_function`
- `information_focus`
- `contrast_target`
- `intensity`
- `prosody_focus`
- `sentence_role_in_article_arc`

### 4.2 禁止把所有演员套入同一参数表

v3 的全局 `PERFORMANCE` 映射在 v4 中不能继续作为最终控制方式。

错误方式：

```text
warm = exaggeration 0.66 / cfg 0.36  # 全员相同
```

正确方式：

```text
DirectorIntent(warm)
        ↓
ActorAdapter(actor_05)
        ↓
05 自己经过标定的 warm 参数与参考声
```

换演员时：

```text
DirectorIntent(warm)
        ↓
ActorAdapter(actor_08)
        ↓
08 自己经过标定的 warm 参数与参考声
```

统一的是导演语义，允许不同演员采用不同模型实现。

---

## 5. Actor Calibration Profile：演员标定档案

这是 v4 的核心基础设施。

### 5.1 每位演员首次入池必须完成一次标定

每位演员必须拥有独立的 `Actor Calibration Profile`，以后所有年份复用。

至少保存：

- actor ID / source speaker
- 角色人格定位
- 年龄气质
- 声音特征
- 最佳 neutral 参考声
- warm / lively / serious / curious / ironic / tense / emotional 等状态的最佳参考声
- 每种状态的 Chatterbox 参数区间
- 可接受的 intensity 范围
- 容易失真的参数区域
- 自然语速区间
- 长句稳定性
- 情绪可塑性
- 角色一致性
- 容易出现的模型缺陷
- human-listening QA 结果
- 是否允许进入正式演员池

### 5.2 演员入池考试

使用统一测试稿测试每一个演员，而不是在真题文章里临时试错。

标准场景至少覆盖：

1. 普通解释
2. 理性分析
3. 温暖交流
4. 故事铺垫
5. 转折
6. 重点强调
7. 克制幽默 / 笑点
8. 严肃评论
9. 引语 / 角色表达
10. 长复杂句

QA 指标包括：

- 真人感
- 声线稳定
- 情绪自然度
- 长句自然度
- 语义重音可控性
- 是否出现机械朗读感
- 是否容易重复 / 截断 / 失真

只有通过标定与听觉验收的演员才能进入正式演员池。

### 5.3 05 的正确定位

05 当前 Text 1 的表现作为第一版真人感 Benchmark。

其他演员不需要“像 05”，但必须在以下维度达到同等级质量门槛：

- 真人感
- 连续性
- 自然节奏
- 情绪可信度
- 角色一致性

若 08 最适合科技文章但当前生成质量不足，则任务是继续标定 08、替换 08 的参考素材或寻找同人格的新演员，而不是把科技文章强行改给 05。

---

## 6. 全篇导演优先于逐句导演

每篇文章先建立 `Article Arc`，再进入句子级控制。

典型结构：

```text
开场状态
→ 论点/叙事展开
→ 转折
→ 信息峰值
→ 结论/笑点/回落
```

逐句导演必须知道当前句在全篇中的位置，禁止每一句孤立贴 `emotion` 标签。

句子内部继续允许按照语义结构分段，但分段依据是：

- 信息焦点变化
- 逻辑转折
- 引语角色变化
- 强对比
- 情绪功能变化

不是简单按逗号或固定长度切分。

---

## 7. Director Intent → Actor Adapter → TTS

v4 新增中间层 `Actor Adapter`。

输入：

```json
{
  "actor_id": "08",
  "director_intent": "curious_probe",
  "intensity": 1,
  "information_focus": ["common sense"],
  "contrast_target": "machine vs human perception"
}
```

Actor Adapter 读取演员标定档案，输出实际 TTS 控制：

- reference clip
- exaggeration
- cfg_weight
- generation seed policy
- temperature / repetition penalty（若该演员有标定差异）
- 可选文本提示策略（若未来引擎支持）

文章编辑层不直接依赖 Chatterbox 参数。

因此未来更换 TTS 引擎时，Article Voice Profile、Director Intent、Actor Calibration 仍可保留，只替换模型适配器。

---

## 8. 连贯性原则

人工静音继续保持 **0**。

禁止：

- 在片段尾部 `apad`
- 固定句间等待
- 用浏览器多个微片段接力制造停顿
- 用后处理 `atempo` 冒充情绪变化

允许：

- 模型自身自然呼吸
- 句法自然停连
- 角色变化时必要的物理分段

最终播放仍以“一句一个最终整句音频”为优先交付单位。

---

## 9. 三层 QA

### 9.1 Technical QA

自动化检查：

- 文件存在
- Opus + MP3 完整
- hash 一致
- 可解码
- 无静音 / 严重 clipping
- 无明显重复或截断
- 音频与文本结构对应

### 9.2 Voice QA

检查：

- 真人感是否达到正式演员池门槛
- actor identity 是否稳定
- 长句是否自然
- 是否出现机器人味
- 情绪是否可信而非表演过度

### 9.3 C Direction QA

检查：

- 是否听得出文章逻辑
- 信息焦点是否突出
- 转折是否成立
- 情绪曲线是否符合全文
- 笑点 / 结论是否正确落下
- 是否真正体现文章人格

只有三层全部通过，状态才允许标为 `C Accepted`。

“全部文件存在”只能称为 `technical complete`。

---

## 10. 逐词时间轴：彻底替代百分比跟读

### 10.1 当前问题

禁止继续使用：

```text
播放百分比 × token 数量 = 当前高亮位置
```

真人语音不匀速，重音、连读、短词、长词和自然停连都会造成累计漂移。

### 10.2 通用方案

所有年份统一采用：

**最终音频 + 已知英文原文 → forced alignment → word-level timestamps**

产物示例：

```json
[
  {"word":"If","start":0.00,"end":0.13},
  {"word":"you","start":0.14,"end":0.22},
  {"word":"are","start":0.23,"end":0.31}
]
```

播放器完全按照真实时间戳推进，不再猜测平均速度。

### 10.3 对齐必须发生在最终音频之后

顺序必须是：

```text
C 生成
→ 合并成最终整句音频
→ QA
→ forced alignment
→ timestamps
→ 发布
```

因为只要音频重生成，旧时间轴就失效。

### 10.4 中文同步

英文使用真实 word timestamps。

中文不做机械字符百分比，而使用已有的双语语义 span 映射：

```text
英文 word/phrase 时间区间
→ 对应中文语义 span
→ 中文同步高亮
```

难词 6+ 的英文词与中文对应译义仍保持绑定。

---

## 11. 通用播放器 v4

播放器必须是独立于年份和文章的基础组件。

固定能力：

- 播放 / 暂停
- 上一句
- 下一句
- 重播
- 0.7 / 1.0 / 1.25 / 1.5 / 2.0 五档磁吸倍速
- 英文真实逐词跟读
- 中文语义同步高亮
- 下滑隐藏 / 上滑恢复
- 轻点句框显示中文
- 长按原生复制
- 句号按钮单句播放

### 11.1 宽度调整

当前手机端播放器接近全宽，需要进一步收窄约 30%。

此调整必须作用于通用 `.player-shell`，而不是给 2002 或 Text 1 写专属 CSS。

目标视觉：**居中悬浮控制岛**，而不是底部大面板。

要求：

- 保持四个圆形 transport 按钮可点击尺寸
- 图标几何居中
- 倍速滑杆仍可顺畅拖动
- 不遮挡正文主要阅读区域
- 小屏设备无横向溢出

---

## 12. 数据层级与职责分离

推荐最终目录职责：

```text
content/
  article_voice_profile.json
  directed_sentences.json

voice-pipeline/
  actors/
    actor-01.json
    actor-02.json
    ...
  director/
    intents.json
  adapters/
    chatterbox_actor_adapter.py
  render/
  alignment/
  qa/

public audio/
  final sentence audio
  manifests with word timestamps
```

职责：

- Article Profile：描述文章
- Director Data：描述表达意图
- Actor Profile：描述演员能力
- Actor Adapter：把导演意图翻译成模型参数
- Renderer：负责生成
- QA：判断是否可发布
- Alignment：只针对最终音频生成时间轴
- Reader：只消费最终 manifest，不参与猜测表演

---

## 13. 2002 母版实施范围

v4 第一阶段不直接批量生产其他年份。

先让 2002 成为完整母版：

1. 为当前正式候选演员建立 calibration profile
2. 用统一 audition 测试演员
3. 把全局 PERFORMANCE 改为 actor-aware adapter
4. 保持“文章决定演员”的 2002 选角原则
5. 按演员标定重新生成需要重做的文章
6. 所有 91 句生成真实 word timestamps
7. 中文语义同步改为时间戳驱动
8. 通用播放器宽度缩约 30%
9. 重新完成 Technical / Voice / C Direction QA
10. 用户确认 2002 达到母版质量

只有 2002 母版通过后，才把生产系统推广到后续年份。

---

## 14. 2003–2026 扩展原则

扩展时不得为每一年重新发明流程。

每年只新增：

- 真题正文数据
- Article Voice Profile
- 文章级 / 句级导演数据
- 选角结果
- 必要时新增并标定新的演员人格

基础设施全部复用：

- 演员池
- 标定档案
- Director Intent
- Actor Adapter
- Renderer
- QA
- Forced Alignment
- Reader UI

如果已有演员池覆盖文章人格，直接调用；只有出现当前演员池无法覆盖的新文章人格时才新增演员。

---

## 15. 非目标

v4 当前不追求：

- 让所有文章都使用不同演员
- 强行使用全部 15 个演员槽位
- 戏剧化广播剧
- 逐句频繁换演员
- 为了“情绪丰富”牺牲自然度
- 通过后期变速制造假情绪
- 对单篇文章写不可复用的 UI/TTS 补丁

---

## 16. 验收标准

### 声音

用户不看屏幕只听声音时，应能自然判断：

- 谁在解释
- 哪里进入故事
- 哪里出现逻辑转折
- 哪里是重点
- 哪里存在克制幽默
- 哪里是结论

且不会感觉演员在“演 TTS”。

### 选角

每篇文章的主讲人必须能说明为什么适合该文章人格，并且演员已经通过自己的 calibration QA。

### 跟读

任意长句、任意演员、任意倍速下，英文高亮都必须基于真实时间戳，不允许随着句子变长产生累计漂移。

### 普适性

同一套生产代码和规则可以直接接受其他年份文章，不需要复制 2002 专属逻辑。

---

## 17. 架构决策摘要

1. **最高原则**：理解文章的人在面对面讲给用户听。
2. **文章决定演员**，05 只作为 Benchmark。
3. **统一导演语义，不统一演员参数。**
4. **每个演员必须先标定，再入演员池。**
5. **Article Arc 优先于逐句 emotion。**
6. **新增 Actor Adapter，解耦导演语义与 Chatterbox 参数。**
7. **三层 QA：Technical / Voice / C Direction。**
8. **最终音频后做 word-level forced alignment。**
9. **英文真实时间轴驱动中文语义高亮。**
10. **播放器作为全局组件，手机端整体宽度再缩约 30%。**
11. **2002 做成母版后，2003–2026 直接复用生产系统。**
