# Codex 0.2：问题研究、交付能力与参数责任设计

## 用户目标
```text
你对参数的偏好偏低，并且你的整体支撑性理解也没有服务于交付质量与交付能力，还在聚焦对我个人用户而言没什么用的形式化保障与形式化安全与形式化软件工程规范等等一系列形式化的偏好。需要对此分支 DIGR 进行更多研究与建设，服务于高质量交付、对任务问题本身的深入焦点研究、流程计划探索研究设计，以及执行能力构建与注意力聚焦保证。
参数的含义也需要研究，特别是参数每单位数值需具备的责任效果范围。
```

## 交付形态与价值
交付可使用的 Codex 候选协议、以问题为中心的辅助工具、参数单位责任说明，以及能直接检视的应用案例。核心价值是让模型更深入地理解问题、比较和修正路线、持续提高实际结果，并在长任务里保持注意力。版本检查和代码测试只服务必要的分发与功能验证。

## 用户纠正与已确认要求
显式 DIGR 的默认起点已由用户选定为 N12/R4/D3/V3，按任务上调；具备真实能力和授权时优先 L3。不能把高投入换成更多形式记录，也不能提高数值后缩小每单位的实际责任。普通任务默认轻量；当前工作在独立候选分支完成，不自动切换生产 stable。

## 当前关键问题
怎样让高投入真正转化为有内容的问题研究、流程设计与成品改进？参数的不同单位分别负责到什么范围？辅助工具怎样帮助注意力和原材料使用，而非制造新的维护工作？

## 研究、竞争解释与方案

### 对上一版问题的判断
0.1 主要实现了分发检查、轮次预览和能力描述；其工作记忆建议偏向状态和证明。深入研究、计划探索和成品改进缺少足够明确的行为支撑。较低投入和宽泛的单位含义又给过早停止留下了空间。改进目标包括执行语义和实际工作工具，不能只换语气或提高计数。

竞争方向一：只把 N/R/D/V 调高。单独采用会增加碎片化计数的诱因，仍可能沿错误问题继续做很多工作。

竞争方向二：建立更完整的记录/校验框架。单独采用会把注意力继续留在框架自身，不能回答当前任务的核心问题。

采用方向：以用户用途和当前高价值问题组织原生研究，明确每单位责任；发展竞争解释与可行路线，通过实际材料和代表性试作改变方案；用高投入抑制早停，用轻量工作上下文支持持续深入。

### 问题研究与流程探索
[Anthropic 的 prompting guidance](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#research-and-information-gathering)建议复杂研究发展竞争假设并修正研究计划。本版采用这一思路，具体要求寻找能区分解释的材料和试作，并把发现带回当前方案。它没有被移植成固定假设树、分数或所有任务必经的阶段。

[OpenAI 的 Codex best practices](https://learn.chatgpt.com/docs/learn/best-practices#plan-first-for-difficult-tasks)强调困难任务的前期理解与计划。本版把流程本身作为可研究对象：适用条件、依赖、质量上限、投入和真实用户用途都可被重新研究。软件工程中的具体程序只在对应任务有帮助时取用。

研究质量不仅是找到支持当前方案的资料。对能改变路线的问题追查反例、分歧与原始内容，试作有代表性的候选，必要时重组整项工作。主线保持智能判断权，没有算法调度器替它选择思维路线。

### 参数责任尺度
本地比较了 stable/main 的结果主权、主线演进、候选、R、D、V 和 L 原始定义。main 明确把 R 指向整个候选及其路线，把 D 指向非局部介入，把 V 指向持续异质线路；N 则是实质主线推进。这些责任边界比“次数多一点”重要。

[参数手册](../codex/PARAMETERS.md)补出了每单位应覆盖的工作整体、影响范围、完成后果、不应计数的微动作，以及参数之间的关系。1N 不按搜索/阅读/记录拆分；1R 不按检查清单分割；1D 不按建议条数计算；1V 不按人数或发言计算；L 是实际信息隔离模式。扎实的排除结论或有依据的保留可以有价值，但忙碌和空话不能冒充后果。

高投入来自用户选择，不伪称经过实验得到最优数值。辅助程序显示偏好和责任文档入口，不给思想质量自动打分，也不据工具次数认证实质工作。

原始设计来源：[main 的结果主权](https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime/blob/165c95bbbd96d2171687bba073774b211920ef81/core/00_RESULT_SOVEREIGNTY.md)、[R](https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime/blob/165c95bbbd96d2171687bba073774b211920ef81/core/70_REENTRY_AND_ABG.md)、[D](https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime/blob/165c95bbbd96d2171687bba073774b211920ef81/core/75_DISRUPTIVE_GAMBIT.md)、[V](https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime/blob/165c95bbbd96d2171687bba073774b211920ef81/core/76_PERSISTENT_VIEWPOINT.md)、[L](https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime/blob/165c95bbbd96d2171687bba073774b211920ef81/core/77_ISOLATION_LEVELS.md)。

### 注意力、材料与可重开的工作记忆
[Anthropic context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)强调有限注意力中的高相关信息、按需取回材料，以及能继续工作的简明笔记。本版把工作笔记用于存放问题、发现、竞争路线和产物位置，并保留可重开的路径。当前决定是工作认识，可被新证据修正。

[OpenAI 对 skills/prompts 的建议](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)讨论了过度加载指引、重复检查与提前停止。本版按需加载工作台指南，在压缩、研究分叉、重复劳动或注意力偏移时取回关键上下文，不要求每次编辑先维护一组文件。

[Anthropic managed agents](https://www.anthropic.com/research/managed-agents)提醒支撑框架应随模型能力重新审视。本版保留模型对推理和路线的原生控制，辅助工具只扩展信息取用与上下文组织能力，不建立固定规划器或新的宿主服务器。

### 工作台工具的实际职责
`codex_workbench.py init` 从真实委托创建一份可编辑工作笔记。`topics` 定位问题小节；`focus` 带回目标、纠正、当前问题/产物/下一步及选定研究，材料可按原文件行段取用；`challenge` 为 D/V 组合目标与明确选入的事实/候选，不自动复制主线全部理由。

这直接服务于继续思考和实际工作。工具不自动判定哪个问题重要、不替模型搜索所有材料、不选择方案、不派代理、不计数思想贡献。现有搜索、阅读、试作与代理工具继续承担相应行动；工作台帮助它们围绕当前问题配合使用。

## 当前产物与可继续的位置
候选执行协议：[PROTOCOL](../codex/PROTOCOL.md)。每单位责任：[PARAMETERS](../codex/PARAMETERS.md)。工具使用：[WORKBENCH](../codex/WORKBENCH.md)。应用演练：[原资料组装](../codex/examples/assembly/WORK.md)、[责任边界](../codex/examples/UNIT_RESPONSIBILITY.md)。

工作台与候选的相关功能检查已通过，实际验证了取回材料与目标、限制输入范围和加载参数责任文档等行为。用户另已授权并完成小规模独立任务演练，结果和用于修改候选的实际发现见[任务演练](CODEX_TRIAL_RESULTS.md)。读物与岗位判断基本同等可用，单位责任解释有局部差异；不据此宣称全面优于旧版。

## 值得继续的工作
当前已经实际使用工作上下文，完成单位责任区分、两条件任务演练与独立比较，并据发现补充了主产物信息、行动入口和说明方式。候选分支交付这些可以使用的规则、工具和案例；更长任务中的持续效果仍需要实际使用观察，不能以本轮功能检查代答。不要为了增加证明文件而偏离这一目标。
