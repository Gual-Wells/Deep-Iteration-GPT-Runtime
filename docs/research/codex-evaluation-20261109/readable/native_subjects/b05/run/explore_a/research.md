# 附注型阅读作品的语义身份

研究范围：仅 b05 的四题规范、原件、starter 与 task1 本地五次提交。这里是独立探索，不是正式产物、领域完成声明或对其他题的统一改造建议。

## 材料把问题改变在哪里

最初可把 task1 看作找齐三个文件；实际历史迫使问题变成：同一个来源名、同一组段落 ID 和仍然合理的附注，何时已不再构成同一份引文阅读作品？RX-17 的最后一次提交让 original.txt 与 HTML 同步把“the timetable was not a promise”改为“the timetable guaranteed arrival”。两者相互一致，来源头仍称 exact quotation，但它改变了叙事对时刻表可靠性的立场。不能因文件互证而承认原作身份。

n1 保留 deliberate choice 的意图含义；n2 解释保留票据的原因。这两条注释在最后提交中仍可局部成立，因此“注释仍讲得通”也不能给整段原文背书。这里需要同时保留引文本身、段落身份、读者可达路径与注释关联；任一局部的成功不可替代其他关系。

## 已检查的具体结果

identity_matrix.json 按新到旧保留五个完整提交的实算结果：

- ed6c24ba96f4b5e6bde4db45c7c9018598a168ba：原文与展示共同改写；跳转和注释并未因此消失。
- 154c6c71bcb1573f350a25f702adb952cfde6dff：原文和注释存在，但第二导航与 jumps.json 一起指向不存在的 p9。
- 1eb919e2197feef5fb43b900e245cbcd8d9e923a：原文与导航保留，notes.json 缺失。
- 3e68f52cec21d59778233a547d051125cd107820：四类材料及关联均保留，是满足本次委托的最新历史作品版本。
- bea68ce517a670aa862fb597fadcd664a08eb50e：同样合格，但较旧。

选中版本与初始版的 original.txt、HTML、jumps.json、notes.json 字节相同；CSS 改变并新增 release.txt。它说明作品身份保留允许呈现演进，不能把“越旧越真”或“任何差异都不许”当规则。正式导出应来自选中提交的六个受追踪文件：index.html、jumps.json、notes.json、original.txt、reader.css、release.txt；本研究没有生成导出物。

## 可检查试作与反例

consistency_traps.json 记录三种对照：

1. 实际 HEAD：HTML 段落与自身 original.txt 一致=true；与 reference 原作一致=false。内部一致性不能识别共同漂移。
2. 实际 154c 提交：jumps.json 与 nav 一致=true；全部目标存在=false，缺 p9。两份配置相同仍可能共同失效。
3. 仅在内存构造的附注交换：文字集合、笔记 ID 集合、目标段落 ID 集合全保留；n1/p1 与 n2/p2 关联被交换。输入从未改动。清点对象不能识别关系损坏。

没有把另一题的规范硬套进来：task4 在冻结前明确要求换行规范化，task1 的 original.txt 则明确要求字节相同。两种身份边界由具体委托决定，不应自动推广一种统一的文本清洗或哈希规则。

## 下一次研究值得追的问题

Main 形成候选后，可独立重读压缩包内的真实六文件，核对它是否构成同一个提交的阅读作品，而不只复读 choice.json；特别检查完整文件集合、原文与 HTML 的双重保真，以及 n1/p1、n2/p2 的关联。若未来允许重写，值得另问“来源仍可称 exact quotation 吗、注释应随文本变化还是保留版本”，但当前委托没有授权重写，不能据此修补 HEAD。

实测边界：没有浏览器可视化或真实交互测试；HTML 是用标准库解析得到的段落与导航关系。Git HEAD 和工作树状态在研究脚本前后相同。所有 Python 调用使用 -B，未联网、安装依赖或改 output。
