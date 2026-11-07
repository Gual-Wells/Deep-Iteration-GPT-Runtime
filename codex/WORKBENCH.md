# 用于深入研究和注意力聚焦的工作台

长任务优先复用已有工作笔记。需要一个直接可用的起点时，使用 `tools/codex_workbench.py`。工具读取一份普通 Markdown，把用户目标、当前关键问题、已有发现和指定原材料组合起来，帮助继续研究或制作；模型自己选择问题和路线。

## 一份工作笔记足够开始

笔记包含用户原始目标、交付价值、用户纠正、当前关键问题、研究与竞争方案、实际产物和下一步。研究部分自由写：可以用问题、假设、材料比较、试作结果或其他适合任务的组织方式。保留已经搁置但有重开价值的路线，不把决定当永久事实。

每次有重要发现时，说明它为什么影响当前方案或成品。不要把笔记填成命令流水账，不要求每轮另建文件。来源以直达的文件路径、章节/页段、URL或实验结果为主，按需读取，不以整理完整资料库为前提。PDF/EPUB 用实际可用阅读与切分工具直接处理；本工具不要求先全文转成文本。

## 初始化和取回当前问题

以下路径只是示例，实际文件放本任务的数据盘工作区：

```text
python -B tools/codex_workbench.py init --request D:/task/request.txt --work D:/task/WORK.md
python -B tools/codex_workbench.py topics --work D:/task/WORK.md
python -B tools/codex_workbench.py focus --work D:/task/WORK.md --topic "原页组装路线" --material D:/task/notes.md:20-45
```

初始化保留原始委托，已有工作台不会被覆盖。随后直接编辑 WORK.md，原材料无须复制进目录。topics 给出小节位置；focus 始终带回用户目标、交付用途与纠正，再带回当前问题、产物、下一步和选中的研究小节。材料逐行标出原位置，便于继续追究和取证。

工具不自动猜测哪条路线值得做；用 rg 或已有检索找到相关内容，再选入对当前问题有价值的范围。材料相对路径以工作台文件所在目录为基准；也可直接传绝对路径。上下文较长时选小节/材料行段；不会静默截掉目标和纠正。确有必要时可以提高字符预算。

已有文档无需改造成模板。可用 `focus --work D:/task/existing-notes.md --request D:/task/request.txt --topic "现有文档中的问题标题"`，直接组合真实委托与选定小节；challenge 也接受单独的 request 文件。其余材料与最新要求由模型按当前问题选入，不要求先重整项目文件。

## 给 D/V 提供足以独立研究的输入

```text
python -B tools/codex_workbench.py challenge --kind D --work D:/task/WORK.md --question "保留原页直接组装能否改变当前生产路线？实际比较可行方法。" --candidate D:/task/current-plan.md --material D:/task/source-notes.md:1-30
python -B tools/codex_workbench.py challenge --kind V --work D:/task/WORK.md --question "从真实学习过程研究，当前编排是否掩盖了跨章节依赖？持续发展这一视角。" --material D:/task/source-notes.md:31-60
```

D/V 输入默认带用户目标、交付价值和用户纠正，附加本次问题及显式选入的候选/材料。不会自动灌入主线全部研究过程、推导理由和下一步设想。模型需要选入足够事实，让新的研究既有基础，也保留不同问题表征的空间。

这些输入可以用于已有授权下的真实独立代理，也可以辅助原生模型发展语义上不同的研究。工具本身不派代理、不调用模型 API、不声称已完成 D/V 或达到 L3。真正效果体现在后续研究、方案、实物和主线处理，单位责任见 PARAMETERS。

## 在什么时候用

当任务跨很多材料、研究分叉、准备重开方案、上下文压缩或开始偏离原问题时使用。短任务直接处理即可。不要把调用工作台变成每次编辑前的新仪式，也不要为维护笔记停下可以直接完成的实质工作。

## 顺手留下有用的讨论与执行后果

直接编辑同一份笔记即可。可选 `record` 将一段公开摘要追加到已存在且唯一的小节，供原有 `topics/focus` 取回，不另建事件数据库：

```text
python -B tools/codex_workbench.py record --work D:/task/WORK.md --topic "原页组装路线" --kind "异议与取舍" --text-file D:/task/note.txt --ref D:/task/sample.pdf
python -B tools/codex_workbench.py focus --work D:/task/WORK.md --topic "原页组装路线"
```

标题自由写，不是必须遍历的事件类型。正文可写：返回发现A；Main采用B、暂缓C，因为D；实际修改E，或E尚待落实；条件F发生时重开C。重要的灵感可以只留下待区分的问题。用户纠正、方案变化和可复用教训保留相应条件与依据，不要求每次命令、发言、测试都记录。

工具以引用段落保存正文，正文中的标题不会误变成工作台小节；父节记录放在第一个子节之前，避免误归最后一个子节。保留原笔记和原来的UTF-8 BOM/换行。时间戳只是这次记录的时间，不证明有效工作时长。小节不存在或有重名则不写入；它不自动创建分类树。

这是单一主线写入的便利工具，不支持多个代理同时改同一笔记。代理通过现有消息/结果文件返回，主线决定怎样综合。工具不推断未处理关系、不认证采纳已经落实、不自动统计 N/R/D/V。需要关系检索时，可按当前问题选择材料或另用确有收益的索引；不能从“有日志”推出“任务已完成”。
