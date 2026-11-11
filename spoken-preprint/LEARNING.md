# 从听见情节到理解并取用语言

原场景提供真实生成的虚构交流；学习编辑另做解释、对照与处境检索，不冒充原人物发言，不认证用户收益。

新书可用 learning_contract(schema_version:1) 写 target_domain/why_relevant/difficulty_focus/intended_uses。领域要具体：端侧推理实习面试的技术对象不能靠通用面试礼貌替代。准确的专家交流若省略艰难中间过程，也可退回；不强造失败次数。

```text
python -B tools/codex.py preprint cases --root <book> --input <cases.json> --expected-revision <R> --operation-id cases-v1
python -B tools/codex.py preprint lesson --root <book> --input <lesson.json> --expected-revision <R> --operation-id lesson-v1
python -B tools/codex.py preprint review --root <book> --input <review.json> --expected-revision <R> --operation-id review-v1
python -B tools/codex.py preprint learning-status --root <book>
python -B tools/codex.py preprint study-status --root <book>
python -B tools/codex.py preprint find --root <book-A> --root <book-B> --query "还没想清楚怎样先澄清"
```

使用实际 revision；同 operation ID 只可重试相同输入。源变后重新阅读，不给旧判断换新哈希继续用。

cases 输入含 cases 列表，可附 series_relations。每个 case 有 id/cue（中文处境）/intent/why_hard/what_changed/event_ids/usage。event_ids 要保留一段连续公开投影，至少两轮 speech，不省略中间回应或动作。usage 逐项给 event_id/surface/meaning/function/conditions/register/frequency_status，可附作者 variants{text,explanation} 与 public_sources。解释实际指代、义项和语气；没有语料证据就标未核实，不给伪造词频排名。

系列关系：exact-use 保存同一实际表达两端的义项/条件；handling-function 表示不同说法承担相近动作；contrastive-use 比较不同义项或处境。后两者不算词汇复现，三者都不表示用户掌握。关系带 id/kind/source_case_id/target_root/target_case_id/explanation/differences；exact-use 与 contrastive-use 另给两端 surface，冻结具体片段。find 只搜显式根，目标未包含时不冒称已核查。书面回看不暴露 target_root 私人绝对路径。

## 独立手机学习稿

为搬迁整个系列，target_root 可写相对本册源目录的路径，例如 `../../another-book/source`；CLI 自动传入实际根，Python status/review_markdown 则用 `root=<actual-book-root>`。沿用绝对路径的旧关系仍可读取。复制两册后，关系核对新位置的目标，不回到原机器路径；缺目标仍明确失效。

lesson 输入带 public_source_sha256（`study.source_digest(state)`）及 lessons。每课有 id/title/author/purpose/sections：source 段给 id/kind:source/purpose/连续 event_ids，由工具提取精确原话，不接受改写；explanation/contrast 段给 id/kind/purpose/text，可用 source_section_ids 指回源段，明确属于编辑作者。

先使具体处境可理解，再拆关键意义差别，回听原句，按需示范有边界的应用。不要求答题或扮演，不逐词加工整部戏。编辑稿更长，篇幅由语言难点决定，不作为效果证明。

先定稿 cases/lesson，再 review：decision useful|revise|reject、reviewer、reason、case_findings（逐项 case_id/judgment/reason）及 content_sha256（`learning.content_digest(state)`）。新书出版要求当前 useful 记录；这是操作者判断绑定，代码不认证质量。场景、课文或相关内容后来改变时过期。

phone/PHONE.txt 是完整原场景；study/PHONE-STUDY.txt 是独立学习听稿；phone/PUBLIC-REVIEW.md 可中文处境查找与细读。来源、真实手机播放、词义理解、临场取用与长期掌握分别报告。
