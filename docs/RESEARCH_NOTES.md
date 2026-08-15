# Research Notes for 2.3.0

2.3.0 的 T 设计参考了以下一手资料/论文，并只吸收与 DIGR 目标一致的原则：

1. OpenAI, **Learning to Reason with LLMs** (2024): 增加推理计算可提高复杂任务能力；推理模型在回答前会使用额外内部推理。
   https://openai.com/index/learning-to-reason-with-llms/
2. OpenAI API docs, **reasoning effort**: reasoning effort 是可调推理强度，降低 effort 通常减少推理 token 并提高速度。说明“推理配置”和“任务规模”是可区分概念。
   https://platform.openai.com/docs/
3. OpenAI, **Deep Research** / system card: agent 通过多步搜索、解释、分析，并根据新信息 pivot；研究深度来自动态工作流而非固定网页数。
   https://openai.com/index/introducing-deep-research/
   https://openai.com/index/deep-research-system-card/
4. Snell et al., **Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters** (2024): 测试时计算策略的有效性强依赖问题难度，自适应 compute allocation 优于统一分配。
   https://arxiv.org/abs/2408.03314
5. Muennighoff et al., **s1: Simple test-time scaling** (2025): budget forcing 表明额外推理有时能修正答案，但其显式 token/停止强制也说明 DIGR 不应把用户 T 简化成固定 token 配额。
   https://arxiv.org/abs/2501.19393
   https://github.com/simplescaling/s1
6. Madaan et al., **Self-Refine** (2023): 同一模型可通过反馈—修订循环改善初稿，支持 DIGR 的结果回代，但固定迭代并非总是最优。
   https://arxiv.org/abs/2303.17651
7. Zhu et al., **Scaling Test-time Compute for LLM Agents** (2025): agent 测试时扩展可提升表现；何时反思、如何验证和多样化 rollout 都影响收益。
   https://arxiv.org/abs/2506.12928
8. Wu et al., **CODA: Difficulty-Aware Compute Allocation for Adaptive Reasoning** (2026): 过度思考简单任务浪费计算，难度感知的自适应分配能在保持质量时降低成本，支持 T 的语义/自适应而非平均分配。
   https://arxiv.org/abs/2603.08659
9. Google Gemini thinking docs (2026): 新模型更倾向 `thinking_level` 等语义强度而非旧式 raw numeric thinking budget，说明抽象层级有从硬 token 数向模型级 reasoning level 演进的趋势。
   https://ai.google.dev/gemini-api/docs/thinking
10. OpenHands / SWE-agent: 工程 agent 使用 max iterations、cost/call limits 等作为运行上限/保险，而不是“质量复杂度”的同义词。DIGR 因此把程序硬限额与语义 T 分离。
   https://github.com/OpenHands/OpenHands
   https://github.com/SWE-agent/SWE-agent
11. dzhng/deep-research 与 qx-labs/agents-deep-research：开源研究 agent 常用 breadth/depth/max_time 作为外部控制，但循环内部仍需根据知识缺口继续搜索。DIGR 2.3 借鉴“知识缺口驱动”，拒绝把 T 直接硬编码成固定 breadth/depth。
   https://github.com/dzhng/deep-research
   https://github.com/qx-labs/agents-deep-research

综合结论：T 应约束“值得展开的有效工作空间”，并由执行模型动态理解；硬上限可以存在于平台层，但不应成为 T 本身。
