# Personal Context：个人资料与能力依据

保存用户**选定的材料、原话及其解释边界**，在需要时只给当前任务或人物一份最小视图。可摄入简历、项目说明、论文、自述、辅学 EPUB 与实际学习观察；资源可用不等于本人掌握，角色表现不回写个人能力。

这是独立的 DIGR Codex 附属。ESP 可直接从选定原件与明确虚构背景创世，也可使用本项目的选段视图；不必先建立整个人的资料库。它不启动 DIGR，不替代模型判断，不调用额外模型 API。

## 使用入口

在 Codex 中给出材料的实际位置和用途，例如：

> 使用 Personal Context，摄入这份简历和项目说明。区分我自己说的、文档声称的、实际观察到的与未知；先给我看用于下一册端侧推理面试场景的资料选段，不把论文或辅学书当成我已经做过的项目。

原件和 `profile.json` 存私人目录。宿主可通过显式路径，或 `$CODEX_HOME/digr-codex/personal-contexts.json` 的导航找到它；导航不是资料本身。工具从当前 checkout 或已安装工具链进入：

```text
python -B tools/codex.py personal --help
python -B tools/codex.py personal init --out <new-private-profile>
python -B tools/codex.py personal source --root <profile> --file <resume.pdf> --origin user_material --pages 1,2 --lineage resume --current --expected-revision 0 --operation-id resume-v1
python -B tools/codex.py personal admit --root <profile> --input <entry.json> --expected-revision <actual-revision> --operation-id selected-claim
python -B tools/codex.py personal view --root <profile> --entries <id1,id2> --purpose <this-use> --audience actor --book <book-id> --role <actor-id> --out <new-capsule.json>
python -B tools/codex.py personal check-view --root <profile> --input <capsule.json> --book <book-id> --role <actor-id>
python -B tools/codex.py preprint bind-context --root <new-book> --actor <actor-id> --input <capsule.json> --expected-revision <actual-revision> --operation-id bind-selected-context
```

占位符换成实际值。先读当前 revision，再变更；相同 operation-id 只能重试相同输入。视图写入新文件，不覆盖旧版。来源、段落和人物绑定的具体字段见[数据契约](DATA.md)。

## 材料读到了多少

- EPUB 默认只登记书名和 spine 目录；`--items` 明确选择 manifest item ID 才提取对应 XHTML 文本块。不是 Apple Books 页码，也未解释图片、公式版式或音频。
- PDF 默认元信息；`--pages` 只取指定的一基页码文本，需要可用的 `pypdf`。扫描件不假称 OCR 成功。
- DOCX 是正文段落，未保留排版页码；JSON 可通过 `--selectors` 选精确路径；文本按行定位。工具提取范围与操作者认真阅读范围另记。
- 不复制整部大文件作为默认入库步骤，也不从缓存恢复用户已移除的隐私原件。当前原件不存在时，报告缺失。

## 版本与使用

每个源版本绑定字节 SHA、来源类型、位置及提取范围。`--lineage resume --current` 是明确选择简历当前版本；旧版本和旧解释仍保留历史。相同字节的归档副本不能掩盖主要原件已改或已删。确实搬动同一版本时，用 `relocate-source` 显式改主位置。

`withdraw-source` 明确撤出一个来源的新使用。撤出、变更、缺失或已被新版本替代的来源不进入新视图；既有 capsule 的 `check-view` 报失效。它不会远程抹除已上传手机的文件或历史出版物。需要移除那些副本时逐一处理实际位置。

视图只选具体条目，保留 claim / self_report / resource / unknown 等身份及来源。演员视图绑定一本书和一个角色；不能把别人、另一本书的胶囊直接复用。一般推理仍可使用，未知不意味着不会。角色自己的虚构内心不能被说成真实用户的内心。

**含个人胶囊的场景按私人出版处理。** 舞台上 public 指该场人物都能听到，不代表允许放进公开 GitHub。没有胶囊的原创虚构例子可单独选择公开。完整个人资料不进 AGENTS.md、公共运行库或全局 Memory。

## 与其它附属的关系

Paper Knowledge 的 `pool.json` 继续负责真实论文学习状态；这里不复制一份掌握表。后续若使用它的观察，保留原位置、具体问题与证据范围。ESP 保存虚构交流及语言资源，书完成、听过或演员成功都不构成学习证据。Voice Companion 仍按用户另行选择的陪练场景进入。

当前工具能验证来源版本、选段、分享范围、人物绑定、修订及重试；不能自动认证文档内容真实、本人当前能力、长期记忆或真实场景迁移。
