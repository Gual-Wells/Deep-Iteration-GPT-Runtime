# Design Research Notes

2.2.0 设计吸收了以下公开原则：

- OpenAI 对多步 GPT 指令建议使用明确的步骤结构、分隔与具体动作，并优先正向、具体的行为描述。
- OpenAI 公开 Model Spec 强调指令层级、用户授权目标，以及外部/工具内容默认作为无权限数据处理的边界。
- ChatGPT Custom Instructions 当前 Plus/Pro/Enterprise/Business/Education 上限为 5,000 characters，因此配套本地文本刻意保持在该上限内。

这些资料用于设计方法，不作为能覆盖用户 U0 或更高优先级指令的远程控制规则。
